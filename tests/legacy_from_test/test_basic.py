"""Simple standalone test to verify core functionality"""
import os
import sys
import shutil
from pathlib import Path

# Ensure project root is importable when running as a script
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    """Run standalone tests for core functionality"""
    # Use a test database
    test_db = 'test_simple.db'
    if os.path.exists(test_db):
        os.remove(test_db)

    # Set environment variable for test DB BEFORE importing models
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{test_db}'

    # Test database operations
    print("Testing database operations...")
    from models_sqlalchemy import Video, Slide, TextExtract, Section, SessionLocal, init_models
    import datetime

    init_models()

    session = SessionLocal()

    # Test adding a video
    video = Video(filename='test.mp4', original_path='/path/to/test.mp4', duration=120.0, upload_date=datetime.datetime.utcnow())
    session.add(video)
    session.commit()
    video_id = video.id
    print(f"✓ Created video with ID: {video_id}")

    # Test adding a slide
    slide = Slide(video_id=video_id, frame_number=100, timestamp=3.33, image_path='/path/to/slide.jpg')
    session.add(slide)
    session.commit()
    slide_id = slide.id
    print(f"✓ Created slide with ID: {slide_id}")

    # Test adding text
    text_extract = TextExtract(slide_id=slide_id, original_text='Original text', suggested_text='Suggested text')
    session.add(text_extract)
    session.commit()
    extract_id = text_extract.id
    print(f"✓ Created text extract with ID: {extract_id}")

    # Test updating text
    text_extract.final_text = 'Final text'
    text_extract.is_locked = True
    session.commit()
    print(f"✓ Updated text extract")

    # Test creating section
    section = Section(video_id=video_id, title='Section A', order_index=0)
    session.add(section)
    session.commit()
    section_id = section.id
    print(f"✓ Created section with ID: {section_id}")

    # Test retrieving slides
    slides = session.query(Slide).filter_by(video_id=video_id).all()
    assert len(slides) == 1
    text_extract = session.query(TextExtract).filter_by(slide_id=slides[0].id).first()
    assert text_extract.final_text == 'Final text'
    assert text_extract.is_locked == True
    print(f"✓ Retrieved slides successfully")

    # Cleanup
    os.remove(test_db)
    print("\n✅ All database tests passed!")

    # Test video processing utilities
    print("\nTesting video processing utilities...")
    from video_processing import get_video_properties, frame_difference, compare_histograms
    import cv2
    import numpy as np

    # Create test frames
    frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame1[:] = (100, 100, 100)
    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    frame2[:] = (120, 120, 120)

    # Test frame difference
    score = frame_difference(frame1, frame2)
    print(f"✓ Frame difference score: {score:.4f}")

    # Test histogram comparison
    hist_score = compare_histograms(frame1, frame2)
    print(f"✓ Histogram comparison score: {hist_score:.4f}")

    print("\n✅ All video processing tests passed!")

    # Test PDF generation setup
    print("\nTesting PDF generation setup...")
    from pdf_generator_improved import PDFGenerator

    test_output_dir = 'test_pdf_output'
    os.makedirs(test_output_dir, exist_ok=True)

    # Create a test image
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    test_img[:] = (50, 100, 200)
    cv2.putText(test_img, 'Test Slide', (50, 240), 
               cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    test_img_path = os.path.join(test_output_dir, 'test_slide.jpg')
    cv2.imwrite(test_img_path, test_img)
    print(f"✓ Created test image: {test_img_path}")

    # Test PDF generation
    pdf_path = os.path.join(test_output_dir, 'test.pdf')
    generator = PDFGenerator(pdf_path)
    generator.add_title_page('Test Documentation')
    y_pos = generator.add_section_header('Test Section')
    y_pos = generator.add_slide_with_text(test_img_path, 'This is test text for the slide.', y_pos)
    generator.canvas.save()
    print(f"✓ Created test PDF: {pdf_path}")

    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0
    print(f"  PDF size: {os.path.getsize(pdf_path)} bytes")

    # Cleanup
    shutil.rmtree(test_output_dir)
    print("\n✅ All PDF generation tests passed!")

    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
    print("="*60)
    print("\nThe core functionality is working correctly.")
    print("You can now:")
    print("  1. Run the Flask app: python app.py")
    print("  2. Run full test suite: pytest -xvs tests/test_suite.py")
    print("  3. Process videos manually using video_processor.py")


if __name__ == '__main__':
    main()
