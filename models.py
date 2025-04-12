from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os
from config import DATABASE_URI
import uuid

Base = declarative_base()

class Track(Base):
    """
    Model representing a saved track in the playlist
    """
    __tablename__ = 'tracks'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    cover = Column(String)
    preview = Column(String)
    link = Column(String)
    is_explicit = Column(Boolean, default=False)
    saved_at = Column(DateTime)
        
    def __repr__(self):
        return f"<Track(id={self.id}, title='{self.title}', artist='{self.artist}')>"
    
    def to_dict(self):
        """Convert track to dictionary for API responses"""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'cover': self.cover,
            'preview': self.preview,
            'link': self.link,
            'is_explicit': self.is_explicit,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None
        }

class UserPreference(Base):
    """
    Model to store user listening preferences and history
    """
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(String(50), nullable=False)
    liked = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    listened_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<UserPreference(track_id={self.track_id}, liked={self.liked}, skipped={self.skipped})>"

# Database initialization function
def init_db():
    """Initialize the database with tables defined in the models"""
    engine = create_engine(DATABASE_URI)
    Base.metadata.create_all(engine)
    return engine

# Session factory
def get_session():
    """Create a new database session"""
    engine = create_engine(DATABASE_URI)
    Session = sessionmaker(bind=engine)
    return Session()