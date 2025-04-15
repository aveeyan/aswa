# Add these imports if not already present
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from modules.deezer_client import DeezerClient
from modules.playlist_manager import PlaylistManager
from models import init_db, get_session, Track, UserPreference, User
import logging
import os
from config import SECRET_KEY, DEBUG
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG

# Add these lines for better session management
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=31)

# Initialize clients
deezer_client = DeezerClient()

# Initialize database
init_db()

# Use a persistent dictionary to store app state across reloads
class AppState:
    def __init__(self):
        self.tracks_preloaded = False

# Create a state object that will persist even during debug reloads
if 'app_state' not in app.config:
    app.config['app_state'] = AppState()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper to get current user
def get_current_user():
    """Helper to get current user with improved error handling"""
    if 'user_id' in session:
        user_id = session.get('user_id')
        if not user_id:
            logger.warning("Empty user_id in session")
            return None
            
        db_session = get_session()
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.warning(f"No user found for id {user_id} in session")
                # Clear invalid session
                session.clear()
                return None
            return user
        except Exception as e:
            logger.error(f"Error retrieving current user: {e}", exc_info=True)
            return None
        finally:
            db_session.close()
    return None

@app.route('/')
def index():
    """
    Main route to render the postcard with tracks
    """
    
    try:
        # Check if we're in test mode
        test_mode = request.args.get('test_mode', 'false').lower() == 'true'
        
        # Get current user if logged in
        current_user = get_current_user()
        
        # Only preload tracks if this is the first request after server start
        if not app.config['app_state'].tracks_preloaded:
            logger.info("First request after server start, preloading tracks...")
            tracks = deezer_client.get_multiple_tracks(20, test_mode=test_mode)
            app.config['app_state'].tracks_preloaded = True
            logger.info("Tracks preloaded successfully")
        else:
            # Use existing tracks instead of fetching new ones
            logger.info("Using cached tracks...")
            tracks = deezer_client.get_cached_tracks()
            if not tracks or len(tracks) == 0:
                # If no tracks in cache (should not happen normally), fetch new ones
                logger.warning("No tracks in cache, fetching new ones...")
                tracks = deezer_client.get_multiple_tracks(20, test_mode=test_mode)
                
        if tracks and len(tracks) > 0:
            # Get the current track index from DeezerClient instead of always using [0]
            current_track_index = deezer_client.get_current_track_index()
            initial_track = tracks[current_track_index] if current_track_index < len(tracks) else tracks[0]
            
            return render_template('index.html',
                tracks=tracks,
                album_link=initial_track.get('link', ''),
                album_isexplicit=initial_track.get('is_explicit', False),
                album_image=initial_track.get('cover_xl', ''),
                album_title=initial_track.get('title', 'Unknown Title'),
                artists=initial_track.get('artist', 'Unknown Artist'),
                album_details=initial_track.get('album', 'Unknown Album'),
                preview_url=initial_track.get('preview', ''),
                test_mode=test_mode,
                current_user=current_user  # Pass the user to the template
            )
        else:
            logger.error("No tracks could be fetched")
            return render_template('error.html', message="Could not fetch tracks"), 500
    except Exception as e:
        logger.error(f"Error in index route: {e}", exc_info=True)
        return render_template('error.html', message="An unexpected error occurred"), 500
@app.route('/next_track')
def next_track():
    """
    Route to get the next track - will return a brand new random track if at the end of the list
    """
    try:
        # Check if we're in test mode
        test_mode = request.args.get('test_mode', 'false').lower() == 'true'
        
        # Fetch the track_id from the request arguments
        track_id = request.args.get('track_id') or request.args.get('id_deezer')
        
        # Get current user
        current_user = get_current_user()
        
        if track_id:
            try:
                # Attempt to mark the current track as skipped if track_id is provided
                if current_user:
                    # If user is logged in, associate the skip with their account
                    success = PlaylistManager.mark_track_skipped(track_id, user_id=current_user.id)
                else:
                    # Anonymous skip
                    success = PlaylistManager.mark_track_skipped(track_id)
                    
                if not success:
                    logger.warning(f"Failed to mark track {track_id} as skipped")
                else:
                    logger.info(f"Track {track_id} marked as skipped successfully")
            except Exception as e:
                logger.error(f"Error marking track {track_id} as skipped: {e}", exc_info=True)

        # Get the next track (it could be the first track in the playlist if we've just started)
        track = deezer_client.get_next_track(test_mode=test_mode)
        
        if track:
            # Validate the track ID before returning it - using id_deezer instead of track_id
            if "id_deezer" not in track or not track["id_deezer"]:
                logger.error(f"Invalid track ID received: {track}")
                return jsonify({"error": "Invalid track ID"}), 400  # Bad Request
            
            # Add track_id field to maintain consistency with other parts of the app
            track["track_id"] = track["id_deezer"]
            
            logger.info(f"Next track fetched: {track}")
            return jsonify(track)  # Return track data in response
        else:
            logger.warning("No tracks available to fetch.")
            return jsonify({"error": "No tracks available"}), 204  # No Content

    except Exception as e:
        logger.error(f"Error in next_track route: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch next track"}), 500  # Internal server error

@app.route('/previous_track')
def previous_track():
    """Route to get previous track"""
    try:
        track = deezer_client.get_previous_track()
        if track:
            return jsonify(track)
        else:
            return jsonify({"error": "No previous track available"}), 204  # No Content
    except Exception as e:
        logger.error(f"Error in previous_track route: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/random_track')
def random_track():
    """Route to get a completely random track"""
    try:
        track = deezer_client.get_random_track()
        if track:
            return jsonify(track)
        else:
            return jsonify({"error": "Could not fetch random track"}), 204  # No Content
    except Exception as e:
        logger.error(f"Error in random_track route: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/save_track', methods=['POST'])
def save_track():
    """Save a track to the user's playlist"""
    try:
        track_data = request.json
        logger.info(f"Received track data for saving: {track_data}")
        
        # Get current user
        current_user = get_current_user()
        
        if not track_data:
            logger.error("No track data provided in the request.")
            return jsonify({"error": "No track data provided"}), 400  # Bad Request
        
        # Ensure track_id is present, otherwise, attempt to derive it
        if "track_id" not in track_data:
            if "id_deezer" in track_data:
                track_data["track_id"] = track_data["id_deezer"]
                logger.info(f"Added track_id using id_deezer value: {track_data['id_deezer']}")
            elif "id" in track_data:
                track_data["track_id"] = track_data["id"]
                logger.info(f"Added track_id using id value: {track_data['id']}")
            elif "deezer_id" in track_data:
                track_data["track_id"] = track_data["deezer_id"]
                logger.info(f"Added track_id using deezer_id value: {track_data['deezer_id']}")
            else:
                # Emergency fallback: Create synthetic track_id using title and artist
                if "title" in track_data and "artist" in track_data:
                    import hashlib
                    synthetic_id = hashlib.md5(f'{track_data["title"]}-{track_data["artist"]}-{track_data["album"]}-{track_data["preview"]}'.encode()).hexdigest()
                    track_data["track_id"] = synthetic_id
                    logger.warning(f"Created synthetic track_id from title and artist: {synthetic_id}")
                else:
                    logger.error("Missing identifying information for synthetic track_id.")
                    return jsonify({"error": "Missing track ID in request data"}), 400  # Bad Request
        
        # Validate track_id before attempting to save
        if not track_data.get("track_id"):
            logger.error(f"Invalid or missing track_id in the track data: {track_data}")
            return jsonify({"error": "Invalid track ID"}), 400  # Bad Request

        # If user is logged in, associate the track with their account
        if current_user:
            track_data['user_id'] = current_user.id

        # Save the track using PlaylistManager
        success, message = PlaylistManager.save_track(track_data)
        
        if success:
            logger.info(f"Track saved successfully: {track_data['track_id']}")
            return jsonify({"message": message}), 201  # Created
        else:
            if "already in playlist" in message:
                logger.info(f"Track {track_data['track_id']} already in playlist.")
                return jsonify({"message": message}), 200  # OK
            else:
                logger.error(f"Failed to save track: {message}")
                return jsonify({"error": message}), 500  # Internal Server Error
    
    except Exception as e:
        logger.error(f"Error saving track: {e}", exc_info=True)
        return jsonify({"error": "Failed to save track: " + str(e)}), 500  # Internal Server Error

@app.route('/playlist')
def playlist():
    """View all saved tracks"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get current user
        current_user = get_current_user()
        user_id = current_user.id if current_user else None
        
        # Get playlist for current user or anonymous
        tracks_list = PlaylistManager.get_playlist(limit, offset, user_id=user_id)
        
        return jsonify(tracks_list)
    except Exception as e:
        logger.error(f"Error retrieving playlist: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve playlist: " + str(e)}), 500

@app.route('/remove_track/<track_id>', methods=['DELETE'])
def remove_track(track_id):
    """Remove a track from the playlist"""
    try:
        # Get current user
        current_user = get_current_user()
        user_id = current_user.id if current_user else None
        
        # Pass track_id directly to the manager, it will handle type conversion
        success, message = PlaylistManager.remove_from_playlist(track_id, user_id=user_id)
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 404
    
    except Exception as e:
        logger.error(f"Error removing track: {e}", exc_info=True)
        return jsonify({"error": "Failed to remove track: " + str(e)}), 500

@app.route('/playlist/view')
def view_playlist():
    """Render the playlist view page"""
    try:
        # Get current user
        current_user = get_current_user()
        
        return render_template('playlist.html', current_user=current_user)
    except Exception as e:
        logger.error(f"Error rendering playlist view: {e}", exc_info=True)
        return render_template('error.html', message="An error occurred loading the playlist"), 500

# Add support for the old route name
@app.route('/liked_music')
def liked_music_redirect():
    """Redirect from old route name to new playlist view"""
    return redirect(url_for('view_playlist'))

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # Get current user if already logged in
    current_user = get_current_user()
    
    # If already logged in, redirect to home
    if current_user:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('login-email')
        password = request.form.get('login-password')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        db_session = get_session()
        try:
            user = db_session.query(User).filter_by(email=email).first()
            
            if user and user.check_password(password):
                # Update last login time
                user.last_login = datetime.datetime.utcnow()
                db_session.commit()
                
                # Set session - Mark session as permanent first
                session.permanent = True
                session.clear()  # Clear any existing session data
                session['user_id'] = user.id
                session['email'] = user.email
                session['name'] = f"{user.first_name} {user.last_name}" if user.first_name else user.email
                
                # Force the session to be saved
                session.modified = True
                
                logger.info(f"User {user.id} ({user.email}) logged in successfully")
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                logger.warning(f"Failed login attempt for email: {email}")
                flash('Invalid email or password', 'error')
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            flash('An error occurred during login', 'error')
        finally:
            db_session.close()
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration"""
    # If already logged in, redirect to home
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('signup-email')
        password = request.form.get('signup-password')
        confirm_password = request.form.get('confirm-password')
        first_name = request.form.get('first-name')
        last_name = request.form.get('last-name')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('login'))
        
        db_session = get_session()
        try:
            # Check if user already exists
            existing_user = db_session.query(User).filter_by(email=email).first()
            if existing_user:
                flash('Email already registered', 'error')
                return redirect(url_for('login'))
            
            # Create new user
            new_user = User(
                id=str(uuid.uuid4()),
                email=email,
                first_name=first_name,
                last_name=last_name,
                created_at=datetime.datetime.utcnow(),
                last_login=datetime.datetime.utcnow()
            )
            new_user.set_password(password)
            
            db_session.add(new_user)
            db_session.commit()
            
            # Mark session as permanent first
            session.permanent = True
            session.clear()  # Clear any existing session data
            
            # Set session
            session['user_id'] = new_user.id
            session['email'] = new_user.email
            session['name'] = f"{new_user.first_name} {new_user.last_name}" if new_user.first_name else new_user.email
            
            # Force the session to be saved
            session.modified = True
            
            logger.info(f"New user created: {new_user.id} ({new_user.email})")
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db_session.rollback()
            logger.error(f"Signup error: {e}", exc_info=True)
            flash('An error occurred during registration', 'error')
        finally:
            db_session.close()
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Handle user logout with improved session clearing"""
    # Get user info for logging before clearing
    user_id = session.get('user_id')
    email = session.get('email')
    
    # Clear session
    session.clear()
    
    # Force the session to be saved
    session.modified = True
    
    if user_id:
        logger.info(f"User {user_id} ({email}) logged out")
    
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/moodboard')
def moodboard():
    """Placeholder for moodboard functionality"""
    current_user = get_current_user()
    return render_template('placeholder.html', title="Moodboard", message="Moodboard feature coming soon!", current_user=current_user)

@app.route('/analytics')
def analytics():
    """Placeholder for analytics functionality"""
    current_user = get_current_user()
    return render_template('placeholder.html', title="Analytics", message="Analytics feature coming soon!", current_user=current_user)

# Add a route to handle health checks
@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"}), 200

# Add an error handler for 404 errors
@app.errorhandler(404)
def page_not_found(e):
    current_user = get_current_user()
    return render_template('error.html', message="Page not found", current_user=current_user), 404

# Add an error handler for 500 errors
@app.errorhandler(500)
def server_error(e):
    current_user = get_current_user()
    return render_template('error.html', message="Server error", current_user=current_user), 500

@app.route('/debug/playlist')
def debug_playlist():
    """Debug endpoint to view the playlist data structure"""
    # Get current user
    current_user = get_current_user()
    user_id = current_user.id if current_user else None
    
    session = get_session()
    try:
        # Filter by user_id if available
        if user_id:
            tracks = session.query(Track).filter_by(user_id=user_id).all()
        else:
            tracks = session.query(Track).all()
            
        track_data = [{
            'track_id': t.track_id,
            'id_deezer': t.id_deezer if hasattr(t, 'id_deezer') else None,
            'title': t.title,
            'artist': t.artist,
            'user_id': t.user_id if hasattr(t, 'user_id') else None
        } for t in tracks]
        return jsonify(track_data)
    finally:
        session.close()

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    current_user = get_current_user()
    return render_template('profile.html', current_user=current_user)

# Remove the problematic debug function that was clearing the tracks_preloaded flag
# if DEBUG:
#     @app.before_request
#     def clear_preloaded_flag():
#         global tracks_preloaded
#         tracks_preloaded = False

# Add a session persistence configuration to ensure sessions work properly in debug mode
if DEBUG:
    app.config['SESSION_TYPE'] = 'filesystem'
    # Increasing session lifetime to prevent quick session expiry
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=31)
    # Make sessions permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True
    
@app.route('/debug/session')
def debug_session():
    """Debug endpoint to view current session data"""
    if not app.debug:
        abort(404)  # Only accessible in debug mode
        
    result = {
        'session_data': dict(session),
        'user_id_in_session': 'user_id' in session,
        'current_user': None
    }
    
    # Try to get current user
    current_user = get_current_user()
    if current_user:
        result['current_user'] = {
            'id': current_user.id,
            'email': current_user.email,
            'name': f"{current_user.first_name} {current_user.last_name}" if current_user.first_name else current_user.email
        }
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=DEBUG)