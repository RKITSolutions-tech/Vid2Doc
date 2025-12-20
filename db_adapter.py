"""Database adapter that prefers SQLAlchemy models when available,
falling back to the legacy database.py functions otherwise.

Usage: import db_adapter as db; use db.get_video_slides(video_id) etc.
"""
try:
    from models_sqlalchemy import SessionLocal, Slide, TextExtract
    SQLA_AVAILABLE = True
except Exception:
    SQLA_AVAILABLE = False

if SQLA_AVAILABLE:
    def get_video_slides(video_id):
        session = SessionLocal()
        try:
            slides = session.query(Slide).filter(Slide.video_id == video_id).order_by(Slide.frame_number).all()
            # Convert to dicts similar to legacy get_video_slides
            out = []
            for s in slides:
                # pick latest text_extract if any
                te = None
                if s.text_extracts:
                    te = s.text_extracts[-1]
                out.append({
                    'id': s.id,
                    'video_id': s.video_id,
                    'frame_number': s.frame_number,
                    'timestamp': s.timestamp,
                    'image_path': s.image_path,
                    'section_id': s.section_id,
                    'original_text': te.original_text if te else None,
                    'suggested_text': te.suggested_text if te else None,
                    'final_text': te.final_text if te else None,
                    'is_locked': te.is_locked if te else 0,
                })
            return out
        finally:
            session.close()
else:
    # Fallback to legacy functions
    from database import get_video_slides

    def get_video_slides(video_id):
        return get_video_slides(video_id)
