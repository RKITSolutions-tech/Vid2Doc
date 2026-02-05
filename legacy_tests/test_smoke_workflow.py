#!/usr/bin/env python
"""
Complete end-to-end smoke test workflow
Processes small_demo_video.mp4, adds sections, edits slide text, adds document text, and exports PDF
"""
import os
import sys
import shutil
from pathlib import Path

# Ensure project root modules are importable when running as a script
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    """Run complete end-to-end smoke test workflow"""
    print("="*70)
    print("COMPLETE END-TO-END SMOKE TEST WORKFLOW")
    print("="*70)

    # Test 1: Check for test video
    print("\n1. Checking for test video...")
    test_video = 'videos/small_demo_video.mp4'
    if not os.path.exists(test_video):
        print(f"✗ Test video not found at: {test_video}")
        print("  This test requires videos/small_demo_video.mp4 to run")
        sys.exit(1)

    video_size = os.path.getsize(test_video) / (1024 * 1024)  # Size in MB
    print(f"✓ Test video found: {test_video}")
    print(f"  Size: {video_size:.2f} MB")

    # Test 2: Setup test environment
    print("\n2. Setting up test environment...")
    test_output_dir = 'test_workflow_output'
    test_db = 'test_workflow.db'

    # Clean up any existing test artifacts
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)
    if os.path.exists(test_db):
        os.remove(test_db)

    os.makedirs(test_output_dir, exist_ok=True)

    # IMPORTANT: Set SQLAlchemy database URI BEFORE importing any modules that use it
    # This ensures pdf_generator_improved.py uses the test database
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(test_db)}'

    print(f"✓ Test environment ready")

    # Test 3: Initialize database
    print("\n3. Initializing test database...")
    try:
        from vid2doc.database import init_db
        import vid2doc.database as database
        
        # Use test database
        database.DATABASE_PATH = test_db
        init_db()
        
        # Also initialize SQLAlchemy models with the test database
        from vid2doc.models_sqlalchemy import init_models
        init_models()
        
        assert os.path.exists(test_db)
        print(f"✓ Test database created: {test_db}")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        sys.exit(1)

    # Test 4: Process the video
    print("\n4. Processing small_demo_video.mp4...")
    print("   This may take a minute or two...")
    try:
        from vid2doc.video_processor import VideoProcessor
        
        processor = VideoProcessor(test_video, test_output_dir)
        video_id = processor.process_video()
        
        print(f"✓ Video processed successfully")
        print(f"  Video ID: {video_id}")
    except Exception as e:
        print(f"✗ Video processing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 5: Verify slides were extracted
    print("\n5. Verifying extracted slides...")
    try:
        from vid2doc.database import get_video_slides
        
        slides = get_video_slides(video_id)
        num_slides = len(slides)
        
        if num_slides == 0:
            print("✗ Error: No slides extracted from video")
            print("  Cannot continue with workflow test")
            sys.exit(1)
        
        print(f"✓ Extracted {num_slides} slides from video")
        
        # Show first 3 slides
        for i, slide in enumerate(slides[:3], 1):
            print(f"\n  Slide {i}:")
            print(f"    Frame: {slide['frame_number']}")
            print(f"    Time: {slide['timestamp']:.2f}s")
            print(f"    Image: {os.path.basename(slide['image_path'])}")
        
        if num_slides > 3:
            print(f"\n  ... and {num_slides - 3} more slides")
        
        # Verify slide images exist
        missing_images = [s for s in slides if not os.path.exists(s['image_path'])]
        if missing_images:
            print(f"✗ Error: {len(missing_images)} slide images are missing")
            sys.exit(1)
        else:
            print(f"✓ All slide images exist on disk")
        
    except Exception as e:
        print(f"✗ Slide verification failed: {e}")
        sys.exit(1)

    # Test 6: Add sections
    print("\n6. Adding sections...")
    try:
        from vid2doc.database import create_section, assign_slide_to_section
        
        # Create sections
        section_intro = create_section(video_id, "Introduction", 0)
        section_main = create_section(video_id, "Main Content", 1)
        section_conclusion = create_section(video_id, "Conclusion", 2)
        
        print(f"✓ Created 3 sections:")
        print(f"  - Introduction (ID: {section_intro})")
        print(f"  - Main Content (ID: {section_main})")
        print(f"  - Conclusion (ID: {section_conclusion})")
        
        # Assign slides to sections
        third = num_slides // 3
        for i, slide in enumerate(slides):
            if i < third:
                section_id = section_intro
            elif i < 2 * third:
                section_id = section_main
            else:
                section_id = section_conclusion
            assign_slide_to_section(slide['id'], section_id)
        
        print(f"✓ Assigned {num_slides} slides to sections")
        
    except Exception as e:
        print(f"✗ Section creation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 7: Edit slide text
    print("\n7. Editing slide text...")
    try:
        from vid2doc.database import get_text_extract_by_slide, update_text_extract, add_text_extract
        
        slides_edited = 0
        
        # Edit text for first 3 slides (or all if less than 3)
        for i, slide in enumerate(slides[:min(3, num_slides)]):
            slide_id = slide['id']
            
            # Get existing text extract or create one
            text_extract = get_text_extract_by_slide(slide_id)
            
            if text_extract:
                extract_id = text_extract['id']
                new_text = f"Edited text for slide {i+1}: This slide has been updated with custom content."
                update_text_extract(extract_id, new_text, is_locked=True)
                slides_edited += 1
            else:
                # Create a text extract if none exists
                extract_id = add_text_extract(
                    slide_id, 
                    original_text=f"Original text for slide {i+1}",
                    suggested_text=f"Edited text for slide {i+1}: This slide has been updated with custom content."
                )
                # Now update it with the final text
                update_text_extract(extract_id, f"Edited text for slide {i+1}: This slide has been updated with custom content.", is_locked=True)
                slides_edited += 1
        
        print(f"✓ Edited and locked text for {slides_edited} slides")
        
    except Exception as e:
        print(f"✗ Slide text editing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 8: Add document text
    print("\n8. Adding document text...")
    try:
        from vid2doc.database import update_video_document
        
        document_title = "Smoke Test Video Documentation"
        document_summary = """
This is a comprehensive smoke test of the video documentation system.
This test processes a real video, extracts slides, organizes them into sections,
edits slide text, and generates a professional PDF document.

Key features tested:
- Video processing and slide extraction
- Section creation and organization
- Text editing and locking
- Document metadata
- PDF generation with images and text
"""
        
        update_video_document(video_id, document_title, document_summary)
        
        print(f"✓ Added document title and summary")
        print(f"  Title: {document_title}")
        print(f"  Summary length: {len(document_summary)} characters")
        
    except Exception as e:
        print(f"✗ Document text update failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 9: Generate PDF
    print("\n9. Generating PDF export...")
    try:
        from vid2doc.pdf_generator_improved import generate_pdf_from_video_id
        
        pdf_path = os.path.join(test_output_dir, 'smoke_test_workflow.pdf')
        generate_pdf_from_video_id(video_id, pdf_path, document_title)
        
        assert os.path.exists(pdf_path), "PDF file was not created"
        pdf_size = os.path.getsize(pdf_path) / 1024  # Size in KB
        
        print(f"✓ PDF generated successfully")
        print(f"  Path: {pdf_path}")
        print(f"  Size: {pdf_size:.1f} KB")
        
        assert pdf_size > 0, "PDF file is empty"
        print(f"✓ PDF is valid (non-empty)")
        
    except Exception as e:
        print(f"✗ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 10: Verify PDF content
    print("\n10. Verifying PDF content...")
    try:
        # Just check that the file is readable and has reasonable size
        # More detailed PDF validation would require additional libraries
        
        if pdf_size < 10:
            print(f"⚠ Warning: PDF size is very small ({pdf_size:.1f} KB)")
        elif pdf_size > 50000:
            print(f"⚠ Warning: PDF size is very large ({pdf_size:.1f} KB)")
        else:
            print(f"✓ PDF size is reasonable ({pdf_size:.1f} KB)")
        
    except Exception as e:
        print(f"⚠ PDF verification warning: {e}")

    # Test 11: Cleanup
    print("\n11. Cleaning up test artifacts...")
    try:
        # Clean up test artifacts to keep things tidy
        shutil.rmtree(test_output_dir)
        os.remove(test_db)
        print(f"✓ Test artifacts cleaned up")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")

    print("\n" + "="*70)
    print("✅ COMPLETE END-TO-END SMOKE TEST PASSED!")
    print("="*70)
    print(f"""
Successfully completed full workflow:
  ✓ Video processed: small_demo_video.mp4
  ✓ Slides extracted: {num_slides}
  ✓ Sections created: 3
  ✓ Slide text edited: {slides_edited}
  ✓ Document text added
  ✓ PDF generated: {pdf_size:.1f} KB
  ✓ All workflow steps working correctly

The complete video documentation workflow is ready for production!
""")


if __name__ == '__main__':
    main()
