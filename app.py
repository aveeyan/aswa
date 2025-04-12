# Add these imports if not already present
from flask import Flask, render_template, jsonify, request, redirect, url_for
from modules.deezer_client import DeezerClient
from modules.playlist_manager import PlaylistManager
from models import init_db, get_session, Track, UserPreference
import logging
import os
from config import SECRET_KEY, DEBUG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG

# Initialize clients
deezer_client = DeezerClient()

# Initialize database
init_db()

@app.route('/')
def index():
    """
    Main route to generate multiple tracks and render the postcard
    """
    try:
        # Generate a track cycle with more tracks
        tracks = deezer_client.get_multiple_tracks(20)
        if tracks and len(tracks) > 0:
            initial_track = tracks[0]
            return render_template('index.html',
                tracks=tracks,
                album_link=initial_track.get('link', ''),
                album_isexplicit=initial_track.get('is_explicit', False),
                album_image=initial_track.get('cover_xl', ''),
                album_title=initial_track.get('title', 'Unknown Title'),
                artists=initial_track.get('artist', 'Unknown Artist'),
                album_details=initial_track.get('album', 'Unknown Album'),
                preview_url=initial_track.get('preview', '')
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
        # Fetch the track_id from the request arguments
        track_id = request.args.get('id_deezer')  # Changed from 'id' to 'id_deezer' to match data structure
        if track_id:
            try:
                # Attempt to mark the current track as skipped if track_id is provided
                success = PlaylistManager.mark_track_skipped(track_id)
                if not success:
                    logger.warning(f"Failed to mark track {track_id} as skipped")
                else:
                    logger.info(f"Track {track_id} marked as skipped successfully")
            except Exception as e:
                logger.error(f"Error marking track {track_id} as skipped: {e}", exc_info=True)

        # Get the next track (it could be the first track in the playlist if we've just started)
        track = deezer_client.get_next_track()
        
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
        
        tracks_list = PlaylistManager.get_playlist(limit, offset)
        
        return jsonify(tracks_list)
    except Exception as e:
        logger.error(f"Error retrieving playlist: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve playlist: " + str(e)}), 500

@app.route('/remove_track/<track_id>', methods=['DELETE'])
def remove_track(track_id):
    """Remove a track from the playlist"""
    try:
        # Pass track_id directly to the manager, it will handle type conversion
        success, message = PlaylistManager.remove_from_playlist(track_id)
        
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
        return render_template('playlist.html')
    except Exception as e:
        logger.error(f"Error rendering playlist view: {e}", exc_info=True)
        return render_template('error.html', message="An error occurred loading the playlist"), 500

# Add support for the old route name
@app.route('/liked_music')
def liked_music_redirect():
    """Redirect from old route name to new playlist view"""
    return redirect(url_for('view_playlist'))

# Add support for logging in (placeholder for future implementation)
@app.route('/login')
def login():
    """Placeholder for login functionality"""
    return render_template('login.html', message="Login functionality coming soon!")

# Add other placeholder routes
@app.route('/moodboard')
def moodboard():
    """Placeholder for moodboard functionality"""
    return render_template('placeholder.html', title="Moodboard", message="Moodboard feature coming soon!")

@app.route('/analytics')
def analytics():
    """Placeholder for analytics functionality"""
    return render_template('placeholder.html', title="Analytics", message="Analytics feature coming soon!")

# Add a route to handle health checks
@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "ok"}), 200

# Add an error handler for 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found"), 404

# Add an error handler for 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message="Server error"), 500

@app.route('/debug/playlist')
def debug_playlist():
    """Debug endpoint to view the playlist data structure"""
    session = get_session()
    tracks = session.query(Track).all()
    track_data = [{
        'track_id': t.track_id,
        'id_deezer': t.id_deezer if hasattr(t, 'id_deezer') else None,
        'title': t.title,
        'artist': t.artist,
    } for t in tracks]
    return jsonify(track_data)

if __name__ == '__main__':
    app.run(debug=DEBUG)