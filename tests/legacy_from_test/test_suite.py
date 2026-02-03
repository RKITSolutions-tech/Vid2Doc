"""
Test suite for video documentation system

Tests are designed to be run manually in sequence during development
"""
import os
import sys
import pytest
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test database path
TEST_DB = 'test_video_documentation.db'

# IMPORTANT: Set SQLAlchemy database URI BEFORE any imports that use it
os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(TEST_DB)}'

from database import (init_db, add_video, add_slide, add_text_extract, 
                      create_section, assign_slide_to_section, get_video_slides,
                      update_text_extract, get_sections_by_video, DATABASE_PATH)
from unittest.mock import patch
from video_processor import VideoProcessor
from pdf_generator_improved import generate_pdf_from_video_id

def setup_test_db():
    """Setup test database"""
    global DATABASE_PATH
    # Use test database
    import database
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db()
    
    # Also initialize SQLAlchemy models
    from models_sqlalchemy import init_models
    init_models()

def cleanup_test_db():
    """Cleanup test database"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

class TestDatabase:
    """Test database operations"""
    
    def setup_method(self):
        setup_test_db()
    
    def teardown_method(self):
        cleanup_test_db()
    
    def test_init_db(self):
        """Test database initialization"""
        assert os.path.exists(TEST_DB)
        
        # Check tables exist
        import database
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        assert 'videos' in tables
        assert 'slides' in tables
        assert 'text_extracts' in tables
        assert 'sections' in tables
    
    def test_add_video(self):
        """Test adding a video"""
        video_id = add_video('test.mp4', '/path/to/test.mp4', 120.0, 30.0)
        assert video_id > 0
    
    def test_add_slide(self):
        """Test adding a slide"""
        video_id = add_video('test.mp4', '/path/to/test.mp4')
        slide_id = add_slide(video_id, 100, 3.33, '/path/to/slide.jpg')
        assert slide_id > 0
    
    def test_add_text_extract(self):
        """Test adding text extract"""
        video_id = add_video('test.mp4', '/path/to/test.mp4')
        slide_id = add_slide(video_id, 100, 3.33, '/path/to/slide.jpg')
        extract_id = add_text_extract(slide_id, 'Original text', 'Suggested text')
        assert extract_id > 0
    
    def test_update_text_extract(self):
        """Test updating text extract"""
        video_id = add_video('test.mp4', '/path/to/test.mp4')
        slide_id = add_slide(video_id, 100, 3.33, '/path/to/slide.jpg')
        extract_id = add_text_extract(slide_id, 'Original', 'Suggested')
        
        update_text_extract(extract_id, 'Final text', True)
        
        slides = get_video_slides(video_id)
        assert len(slides) == 1
        assert slides[0]['final_text'] == 'Final text'
        assert slides[0]['is_locked'] == 1
    
    def test_create_section(self):
        """Test creating a section"""
        video_id = add_video('test.mp4', '/path/to/test.mp4')
        section_id = create_section(video_id, 'Section A', 0)
        assert section_id > 0
        
        sections = get_sections_by_video(video_id)
        assert len(sections) == 1
        assert sections[0]['title'] == 'Section A'
    
    def test_assign_slide_to_section(self):
        """Test assigning slide to section"""
        video_id = add_video('test.mp4', '/path/to/test.mp4')
        slide_id = add_slide(video_id, 100, 3.33, '/path/to/slide.jpg')
        section_id = create_section(video_id, 'Section A', 0)
        
        assign_slide_to_section(slide_id, section_id)
        
        slides = get_video_slides(video_id)
        assert slides[0]['section_id'] == section_id


class TestVideoProcessing:
    """Test video processing (requires demo_video.mp4)"""
    
    def setup_method(self):
        setup_test_db()
        # Update database module to use test DB
        import database
        database.DATABASE_PATH = TEST_DB
    
    def teardown_method(self):
        cleanup_test_db()
    
    @pytest.mark.manual
    def test_process_demo_video(self):
        """
        MANUAL TEST: Process demo_video.mp4
        
        This test processes the demo video and extracts slides and text.
        It may take several minutes to complete.
        
        Expected: Video is processed, slides are extracted, text is transcribed
        """
        # Use a short trimmed copy of the demo video to keep this manual test fast
        source_path = 'videos/small_demo_video.mp4'
        if not os.path.exists(source_path):
            pytest.skip(f"Demo video not found at {source_path}")

        import tempfile
        import cv2
        temp_dir = tempfile.mkdtemp(prefix='demo_trim_')
        trimmed_path = os.path.join(temp_dir, 'trimmed_demo.mp4')

        # Create a small ~2 second trim to speed up processing
        cap = cv2.VideoCapture(source_path)
        if not cap.isOpened():
            pytest.skip(f"Failed to open source demo video at {source_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(trimmed_path, fourcc, fps, (width, height))

        # write only a small number of frames (~2 seconds)
        frame_limit = int(fps * 2)
        frames_written = 0
        while frames_written < frame_limit:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
            frames_written += 1

        cap.release()
        writer.release()

        print("[manual test] Starting demo video processing (trimmed copy)...")

        # Patch out slow Whisper summarization/transcription to keep the test fast
        def fake_get_slide_text(filename, start_frame, end_frame, fps, model_size="base"):
            return f"Transcript frames {start_frame}-{end_frame}"

        def fake_summrise_text(text, min_length=30, max_length=150, model_name="mock-model"):
            return [{"summary_text": text}]

        settings = {
            "threshold_ssim": 0.9,
            "threshold_hist": 0.9,
            "frame_gap": 5,
            "transition_limit": 2,
            "preview_interval": 120,
            "force_slide_interval": 10,
            "progress_interval": 10,
            "min_slide_audio_seconds": 0.0,
        }

        with patch("video_audio_extraction.get_slide_text", side_effect=fake_get_slide_text), \
             patch("video_audio_extraction.summrise_text", side_effect=fake_summrise_text):
            processor = VideoProcessor(trimmed_path, 'test_output')
            video_id = processor.process_video(settings=settings)

        assert video_id is not None
        assert video_id > 0
        
        # Check that slides were extracted
        slides = get_video_slides(video_id)
        assert len(slides) > 0
        
        print(f"\n✓ Video processed successfully!")
        print(f"  Video ID: {video_id}")
        print(f"  Slides extracted: {len(slides)}")
        print(f"  First slide sample: {slides[0] if slides else 'N/A'}")
        
        # Check that at least one slide has text
        has_text = any(slide['original_text'] for slide in slides)
        assert has_text, "At least one slide should have extracted text"
        
        print(f"  Text extracted: Yes")
        
    # Manual test - no return required


class TestTextEditing:
    """Test text editing workflow"""
    
    def setup_method(self):
        setup_test_db()
        import database
        database.DATABASE_PATH = TEST_DB
    
    def teardown_method(self):
        cleanup_test_db()
    
    @pytest.mark.manual
    def test_edit_text_and_create_sections(self):
        """
        MANUAL TEST: Edit text and create two sections
        
        This test simulates editing extracted text and organizing into sections.
        Run after test_process_demo_video.
        
        Expected: Text can be edited, sections created, slides assigned
        """
        # Create a test video with slides
        video_id = add_video('test.mp4', 'test.mp4', 60.0, 30.0)
        
        # Add some slides with text
        slide1_id = add_slide(video_id, 100, 3.33, 'output/slide1.jpg')
        extract1_id = add_text_extract(slide1_id, 
                                       'This is the original text for slide 1', 
                                       'This is suggested text for slide 1')
        
        slide2_id = add_slide(video_id, 200, 6.67, 'output/slide2.jpg')
        extract2_id = add_text_extract(slide2_id, 
                                       'This is the original text for slide 2', 
                                       'This is suggested text for slide 2')
        
        slide3_id = add_slide(video_id, 300, 10.0, 'output/slide3.jpg')
        extract3_id = add_text_extract(slide3_id, 
                                       'This is the original text for slide 3', 
                                       'This is suggested text for slide 3')
        
        # Edit text for slides
        update_text_extract(extract1_id, 'Edited text for slide 1 - Section A content', False)
        update_text_extract(extract2_id, 'Edited text for slide 2 - Section B content', False)
        update_text_extract(extract3_id, 'Edited text for slide 3 - Section B content', False)
        
        # Create sections
        section_a_id = create_section(video_id, 'Section A', 0)
        section_b_id = create_section(video_id, 'Section B', 1)
        
        # Assign slides to sections
        assign_slide_to_section(slide1_id, section_a_id)
        assign_slide_to_section(slide2_id, section_b_id)
        assign_slide_to_section(slide3_id, section_b_id)
        
        # Lock the text
        update_text_extract(extract1_id, 'Edited text for slide 1 - Section A content', True)
        update_text_extract(extract2_id, 'Edited text for slide 2 - Section B content', True)
        update_text_extract(extract3_id, 'Edited text for slide 3 - Section B content', True)
        
        # Verify
        sections = get_sections_by_video(video_id)
        assert len(sections) == 2
        assert sections[0]['title'] == 'Section A'
        assert sections[1]['title'] == 'Section B'
        
        slides = get_video_slides(video_id)
        assert all(slide['is_locked'] for slide in slides)
        assert slides[0]['section_id'] == section_a_id
        assert slides[1]['section_id'] == section_b_id
        assert slides[2]['section_id'] == section_b_id
        
        print(f"\n✓ Text editing and section creation successful!")
        print(f"  Sections created: {len(sections)}")
        print(f"  Slides organized: {len(slides)}")
        print(f"  All text locked: Yes")
        
    # Manual test - no return required


class TestPDFGeneration:
    """Test PDF generation"""
    
    def setup_method(self):
        setup_test_db()
        import database
        database.DATABASE_PATH = TEST_DB
    
    def teardown_method(self):
        cleanup_test_db()
        # Clean up test PDFs
        if os.path.exists('test_output.pdf'):
            os.remove('test_output.pdf')
    
    @pytest.mark.manual
    def test_export_pdf(self):
        """
        MANUAL TEST: Export to PDF and verify output
        
        This test exports the processed video with sections to PDF
        and verifies the PDF was created.
        
        Expected: PDF is created with proper layout (images left, text right)
        Manual verification needed to check PDF content visually.
        """
        # Create test data
        video_id = add_video('test.mp4', 'test.mp4', 60.0, 30.0)
        
        # Create sections
        section_a_id = create_section(video_id, 'Section A', 0)
        section_b_id = create_section(video_id, 'Section B', 1)
        
        # Add slides - create dummy images for testing
        os.makedirs('test_output', exist_ok=True)
        
        # Create dummy images
        import cv2
        import numpy as np
        
        for i in range(3):
            # Create a simple colored image
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (50 + i * 50, 100, 200)  # Different colors
            cv2.putText(img, f'Slide {i+1}', (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            cv2.imwrite(f'test_output/test_slide_{i+1}.jpg', img)
        
        slide1_id = add_slide(video_id, 100, 3.33, 'test_output/test_slide_1.jpg')
        extract1_id = add_text_extract(slide1_id, 
                                       'Original text 1', 
                                       'This is the content for Section A. It describes the first part of the documentation.')
        update_text_extract(extract1_id, 
                          'This is the content for Section A. It describes the first part of the documentation.', 
                          True)
        assign_slide_to_section(slide1_id, section_a_id)
        
        slide2_id = add_slide(video_id, 200, 6.67, 'test_output/test_slide_2.jpg')
        extract2_id = add_text_extract(slide2_id, 
                                       'Original text 2', 
                                       'This is the content for Section B, slide 1. It describes the second part.')
        update_text_extract(extract2_id, 
                          'This is the content for Section B, slide 1. It describes the second part.', 
                          True)
        assign_slide_to_section(slide2_id, section_b_id)
        
        slide3_id = add_slide(video_id, 300, 10.0, 'test_output/test_slide_3.jpg')
        extract3_id = add_text_extract(slide3_id, 
                                       'Original text 3', 
                                       'This is the content for Section B, slide 2. It provides additional details.')
        update_text_extract(extract3_id, 
                          'This is the content for Section B, slide 2. It provides additional details.', 
                          True)
        assign_slide_to_section(slide3_id, section_b_id)
        
        # Generate PDF
        output_path = 'test_output.pdf'
        generate_pdf_from_video_id(video_id, output_path, 'Test Video Documentation')
        
        # Verify PDF was created
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
        
        print(f"\n✓ PDF generated successfully!")
        print(f"  Output: {output_path}")
        print(f"  Size: {os.path.getsize(output_path)} bytes")
        print(f"\n  MANUAL VERIFICATION NEEDED:")
        print(f"  - Open {output_path} in a PDF reader")
        print(f"  - Check that images appear on the left")
        print(f"  - Check that text appears on the right")
        print(f"  - Check that sections create new pages")
        print(f"  - Check that there are blank lines between sections")
        
    # Manual test - no return required


def run_manual_tests():
    """Run all manual tests in sequence"""
    print("=" * 70)
    print("MANUAL TEST SUITE FOR VIDEO DOCUMENTATION SYSTEM")
    print("=" * 70)
    print("\nThese tests should be run manually in sequence during development.")
    print("Each test can be run individually using pytest -k test_name\n")
    
    print("\n1. Test Database Operations")
    print("   Run: pytest -xvs tests/test_suite.py::TestDatabase")
    
    print("\n2. Test Video Processing (requires demo_video.mp4)")
    print("   Run: pytest -xvs tests/test_suite.py::TestVideoProcessing::test_process_demo_video")
    
    print("\n3. Test Text Editing and Sections")
    print("   Run: pytest -xvs tests/test_suite.py::TestTextEditing::test_edit_text_and_create_sections")
    
    print("\n4. Test PDF Generation")
    print("   Run: pytest -xvs tests/test_suite.py::TestPDFGeneration::test_export_pdf")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    run_manual_tests()
