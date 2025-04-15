from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os
from config import DATABASE_URI
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    """Model representing a user of the application"""
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationship to tracks
    tracks = relationship("Track", back_populates="user")
    
    def set_password(self, password):
        """Create hashed password."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

class Track(Base):
    """
    Model representing a saved track in the playlist
    """
    __tablename__ = 'tracks'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id = Column(String, nullable=False)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    cover = Column(String)
    preview = Column(String)
    link = Column(String)
    is_explicit = Column(Boolean, default=False)
    saved_at = Column(DateTime)
    
    # Foreign key to user
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="tracks")
    
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
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    liked = Column(Boolean, default=False)
    skipped = Column(Boolean, default=False)
    listened_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationship to user
    user = relationship("User")
    
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