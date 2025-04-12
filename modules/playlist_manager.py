from models import get_session, Track, UserPreference
import logging
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)

class PlaylistManager:
    """
    Class to handle all playlist-related operations
    """

    @staticmethod
    def save_track(track_data):
        session = get_session()
        try:
            if 'track_id' not in track_data or not track_data['track_id']:
                logger.error("Invalid track data: missing track_id")
                return False, "Invalid track data: missing track_id"

            track_id = str(track_data['track_id'])
            logger.info(f"Attempting to save track with ID: {track_id}")

            # Check if the track already exists
            existing = session.query(Track).filter_by(track_id=track_id).first()

            if existing:
                logger.info(f"Track {track_id} already exists. Updating saved_at.")
                existing.saved_at = datetime.utcnow()
                session.commit()
                return True, "Track already in playlist, updated timestamp"

            # Create new track
            track = Track(
                track_id=track_id,
                title=track_data.get('title', 'Unknown Title'),
                artist=track_data.get('artist', 'Unknown Artist'),
                album=track_data.get('album', 'Unknown Album'),
                cover=track_data.get('cover', ''),
                preview=track_data.get('preview', ''),
                link=track_data.get('link', ''),
                is_explicit=track_data.get('is_explicit', False),
                saved_at=datetime.utcnow()
            )

            pref = UserPreference(
                track_id=track_id,
                liked=True,
                skipped=False,
                listened_at=datetime.utcnow()
            )

            logger.info(f"Saving new track {track.title} with ID {track_id}")
            session.add(track)
            session.add(pref)
            session.commit()
            return True, "Track added to playlist"

        except IntegrityError as e:
            logger.error(f"Integrity error saving track: {e}")
            session.rollback()
            return False, "Track already exists in playlist (integrity error)"
        except SQLAlchemyError as e:
            logger.error(f"Database error saving track: {e}")
            session.rollback()
            return False, "Database error saving track"
        except Exception as e:
            logger.error(f"Error saving track: {e}")
            session.rollback()
            return False, "Error saving track"
        finally:
            session.close()

    
    @staticmethod
    def get_playlist(limit=50, offset=0):
        """
        Get saved tracks from the playlist
        
        Args:
            limit (int): Maximum number of tracks to return
            offset (int): Offset for pagination
            
        Returns:
            list: List of track dictionaries
        """
        session = get_session()
        try:
            tracks = session.query(Track).order_by(Track.saved_at.desc()).limit(limit).offset(offset).all()
            return [track.to_dict() for track in tracks]
        except Exception as e:
            logger.error(f"Error retrieving playlist: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def remove_from_playlist(track_id):
        """
        Remove a track from the playlist
        
        Args:
            track_id (str): ID of the track to remove
            
        Returns:
            tuple: (success (bool), message (str))
        """
        session = get_session()
        try:
            # Convert track_id to string to ensure consistent type
            track_id = str(track_id)
            
            track = session.query(Track).filter_by(track_id=track_id).first()
            
            if not track:
                return False, "Track not found in playlist"
            
            # Also delete associated preferences
            prefs = session.query(UserPreference).filter_by(track_id=track_id).all()
            for pref in prefs:
                session.delete(pref)
                
            session.delete(track)
            session.commit()
            
            return True, "Track removed from playlist"
        except Exception as e:
            logger.error(f"Error removing track: {e}")
            session.rollback()
            return False, "Error removing track"
        finally:
            session.close()

    @staticmethod
    def mark_track_skipped(track_id):
        """
        Mark a track as skipped in the user preferences database
        
        Args:
            track_id (str): The ID of the track to mark as skipped
            
        Returns:
            bool: True if successfully marked as skipped, False otherwise
        """
        session = None
        try:
            session = get_session()
            
            # Convert track_id to string if it's not already
            track_id = str(track_id)
            
            # Debug logging
            logger.info(f"Marking track {track_id} as skipped")
            
            # Check if this track has a preference record
            existing = session.query(UserPreference).filter_by(
                track_id=track_id
            ).first()
            
            if not existing:
                # Create new preference
                pref = UserPreference(
                    track_id=track_id,
                    liked=False,
                    skipped=True,
                    listened_at=datetime.utcnow()
                )
                session.add(pref)
            else:
                # Update existing preference
                existing.skipped = True
                existing.listened_at = datetime.utcnow()
                
            session.commit()
            logger.info(f"Track {track_id} marked as skipped successfully")
            return True
                
        except Exception as e:
            logger.error(f"Error marking track {track_id} as skipped: {e}", exc_info=True)
            if session:
                session.rollback()
            return False
        finally:
            if session:
                session.close()