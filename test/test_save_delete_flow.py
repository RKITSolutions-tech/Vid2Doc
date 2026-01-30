import os
import tempfile
import shutil
from models_sqlalchemy import Video, Slide, TextExtract, SessionLocal
import datetime


def test_add_save_delete_cycle(db_session):
    # Create a temporary video row to associate slides with
    video = Video(filename='test_video.mp4', original_path='uploads/test', upload_date=datetime.datetime.utcnow())
    db_session.add(video)
    db_session.commit()

    # Add a minimal slide
    slide = Slide(video_id=video.id, frame_number=1, timestamp=0.0, image_path='output/slide_1.jpg')
    db_session.add(slide)
    db_session.commit()

    # Verify slide was added
    assert slide.id is not None
    assert slide.video_id == video.id

    # Add and update a text extract
    text_extract = TextExtract(slide_id=slide.id, original_text='orig', final_text='final_text_test', is_locked=False)
    db_session.add(text_extract)
    db_session.commit()

    # Confirm the text extract is associated
    db_session.refresh(slide)
    assert len(slide.text_extracts) == 1
    assert slide.text_extracts[0].final_text == 'final_text_test'

    # Delete the slide (this should cascade delete text extracts if configured, but for now manual)
    db_session.delete(text_extract)
    db_session.delete(slide)
    db_session.commit()

    # Ensure slide no longer exists
    deleted_slide = db_session.query(Slide).filter_by(id=slide.id).first()
    assert deleted_slide is None

    # Cleanup: remove the video row we created
    db_session.delete(video)
    db_session.commit()
