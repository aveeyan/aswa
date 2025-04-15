# modules/playlist_manager.py
from models import Track, UserPreference, get_session
import datetime
import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

logger = logging.getLogger(__name__)

class PlaylistManager:
    """
    Class to handle all playlist-related operations
    """
    
    @staticmethod
    def save_track(track_data):
        """
        Save a track to the user's playlist
        
        Args:
            track_data (dict): Track data including track_id, title, artist, etc.
            
        Returns:
            tuple: (success, message)
        """
        session = get_session()
        try:
            # Ensure we have track_id - this is critical
            if not track_data or not track_data.get('track_id'):
                logger.error("Invalid track data: missing track_id")
                return False, "Invalid track data: missing track_id"
            
            track_id = str(track_data['track_id'])
            # Handle both anonymous and logged-in users
            user_id = track_data.get('user_id', 'anonymous')
            
            logger.info(f"Attempting to save track with ID: {track_id} for user: {user_id}")
            
            # Check if track already exists for this user
            existing_track = session.query(Track).filter_by(
                track_id=track_id,
                user_id=user_id
            ).first()
            
            if existing_track:
                logger.info(f"Track {track_id} already exists for user {user_id}. Updating saved_at.")
                existing_track.saved_at = datetime.datetime.utcnow()
                session.commit()
                return True, "Track already in playlist, updated timestamp"
            
            # Create a new track entry
            new_track = Track(
                track_id=track_id,
                title=track_data.get('title', 'Unknown Title'),
                artist=track_data.get('artist', 'Unknown Artist'),
                album=track_data.get('album', 'Unknown Album'),
                cover=track_data.get('cover_xl', track_data.get('cover', '')),
                preview=track_data.get('preview', ''),
                link=track_data.get('link', ''),
                is_explicit=track_data.get('is_explicit', False),
                saved_at=datetime.datetime.utcnow(),
                user_id=user_id
            )
            
            # Also record the user preference
            new_preference = UserPreference(
                track_id=track_id,
                user_id=user_id,
                liked=True,
                skipped=False,
                listened_at=datetime.datetime.utcnow()
            )
            
            logger.info(f"Saving new track {new_track.title} with ID {track_id} for user {user_id}")
            session.add(new_track)
            session.add(new_preference)
            session.commit()
            
            return True, "Track saved successfully"
            
        except IntegrityError as e:
            logger.error(f"Integrity error saving track: {e}")
            session.rollback()
            return False, "Track already exists in playlist (integrity error)"
        except SQLAlchemyError as e:
            logger.error(f"Database error saving track: {e}")
            session.rollback()
            return False, f"Database error saving track: {str(e)}"
        except Exception as e:
            logger.error(f"Error saving track: {e}", exc_info=True)
            session.rollback()
            return False, f"Error saving track: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def get_playlist(limit=50, offset=0, user_id=None):
        """
        Get a user's playlist with pagination
        
        Args:
            limit (int): Max number of tracks to return
            offset (int): Offset for pagination
            user_id (str): ID of the user whose playlist to retrieve
            
        Returns:
            list: List of track dictionaries
        """
        if not user_id:
            # For anonymous users, use special user_id
            user_id = 'anonymous'
            logger.info("Using anonymous user_id for get_playlist")
            
        session = get_session()
        try:
            tracks = session.query(Track).filter_by(user_id=user_id).order_by(
                Track.saved_at.desc()
            ).offset(offset).limit(limit).all()
            
            return [track.to_dict() for track in tracks]
            
        except Exception as e:
            logger.error(f"Error retrieving playlist: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    @staticmethod
    def remove_from_playlist(track_id, user_id=None):
        """
        Remove a track from the user's playlist
        
        Args:
            track_id (str): ID of the track to remove
            user_id (str): ID of the user whose playlist to modify
            
        Returns:
            tuple: (success, message)
        """
        if not track_id:
            logger.error("Track ID is required for removal")
            return False, "Track ID is required"
            
        # For anonymous users
        if not user_id:
            user_id = 'anonymous'
            
        session = get_session()
        try:
            # Convert track_id to string for consistency
            track_id = str(track_id)
            
            track = session.query(Track).filter_by(track_id=track_id, user_id=user_id).first()
            
            if not track:
                logger.info(f"Track {track_id} not found in user {user_id}'s playlist")
                return False, "Track not found in playlist"
                
            # Remove the track
            session.delete(track)
            
            # Also remove or update preferences
            preference = session.query(UserPreference).filter_by(track_id=track_id, user_id=user_id).first()
            if preference:
                session.delete(preference)
                
            session.commit()
            logger.info(f"Track {track_id} removed from user {user_id}'s playlist")
            return True, "Track removed from playlist"
            
        except Exception as e:
            logger.error(f"Error removing track: {e}", exc_info=True)
            session.rollback()
            return False, f"Error removing track: {str(e)}"
        finally:
            session.close()
    
    @staticmethod
    def mark_track_skipped(track_id, user_id=None):
        """
        Mark a track as skipped for a user
        
        Args:
            track_id (str): ID of the track that was skipped
            user_id (str): ID of the user who skipped the track
            
        Returns:
            bool: Success status
        """
        if not track_id:
            logger.error("Track ID is required for marking as skipped")
            return False
            
        # Handle anonymous users
        if not user_id:
            user_id = 'anonymous'
            
        session = get_session()
        try:
            # Check if track_id is a string or int/numeric
            try:
                track_id = str(track_id)
            except Exception as e:
                logger.error(f"Invalid track_id format: {e}")
                return False
            
            logger.info(f"Marking track {track_id} as skipped for user {user_id}")
            
            # Check if preference exists
            preference = session.query(UserPreference).filter_by(
                track_id=track_id, 
                user_id=user_id
            ).first()
            
            if preference:
                # Update existing preference
                preference.skipped = True
                preference.listened_at = datetime.datetime.utcnow()
            else:
                # Create new preference
                new_preference = UserPreference(
                    track_id=track_id,
                    user_id=user_id,
                    liked=False,
                    skipped=True,
                    listened_at=datetime.datetime.utcnow()
                )
                session.add(new_preference)
                
            session.commit()
            logger.info(f"Track {track_id} marked as skipped successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking track {track_id} as skipped: {e}", exc_info=True)
            session.rollback()
            return False
        finally:
            session.close()