"""SQLAlchemy models for Slides and TextExtracts (migration start).

This module defines ORM models that map to the existing sqlite tables. It is
intended to be used alongside the current `database.py` until migration is
complete.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    ForeignKey,
    DateTime,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

BASE_DIR = os.path.abspath(os.getcwd())
DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', f'sqlite:///{os.path.join(BASE_DIR, "video_documentation.db")}')

engine = create_engine(DATABASE_URI, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def reinit_engine(new_database_uri=None):
    """Reinitialize the SQLAlchemy engine with a new database URI.
    
    This is useful for testing when you need to switch to a different database
    after the module has been imported.
    
    Args:
        new_database_uri: The new database URI to use. If None, re-reads from
                         the SQLALCHEMY_DATABASE_URI environment variable.
    """
    global engine, SessionLocal, DATABASE_URI
    
    if new_database_uri:
        DATABASE_URI = new_database_uri
    else:
        DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 
                                 f'sqlite:///{os.path.join(BASE_DIR, "video_documentation.db")}')
    
    engine = create_engine(DATABASE_URI, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Section(Base):
    __tablename__ = 'sections'
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)
    create_new_page = Column(Boolean, default=False)
    created_at = Column(DateTime)
    video = relationship('Video', backref='sections')
    slides = relationship('Slide', backref='section', order_by='Slide.frame_number')

    def __repr__(self):
        return f'<Section(id={self.id}, title={self.title})>'


class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    duration = Column(Float, nullable=True)
    upload_date = Column(DateTime, nullable=False)
    processed = Column(Boolean, default=False)
    slides = relationship('Slide', backref='video', order_by='Slide.frame_number')

    def __repr__(self):
        return f'<Video(id={self.id}, filename={self.filename})>'


class Slide(Base):
    __tablename__ = 'slides'
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False)
    image_path = Column(String, nullable=False)
    section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    text_extracts = relationship('TextExtract', back_populates='slide', order_by='TextExtract.created_at')

    def to_dict(self):
        return {
            'id': self.id,
            'video_id': self.video_id,
            'frame_number': self.frame_number,
            'timestamp': self.timestamp,
            'image_path': self.image_path,
            'section_id': self.section_id,
        }


class TextExtract(Base):
    __tablename__ = 'text_extracts'
    id = Column(Integer, primary_key=True)
    slide_id = Column(Integer, ForeignKey('slides.id'), nullable=False)
    original_text = Column(Text)
    suggested_text = Column(Text)
    final_text = Column(Text)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    slide = relationship('Slide', back_populates='text_extracts')

    def to_dict(self):
        return {
            'id': self.id,
            'slide_id': self.slide_id,
            'original_text': self.original_text,
            'suggested_text': self.suggested_text,
            'final_text': self.final_text,
            'is_locked': self.is_locked,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


def init_models():
    Base.metadata.create_all(bind=engine)


if __name__ == '__main__':
    init_models()
