#!/usr/bin/env python
"""Demo script to process demo_video.mp4"""
import os
import sys

# Check if demo video exists
demo_video = 'videos/demo_video.mp4'

if not os.path.exists(demo_video):
    print(f"❌ Demo video not found at: {demo_video}")
    print("\nThis script expects a demo_video.mp4 file in the videos/ directory")
    sys.exit(1)

print("="*70)
print("VIDEO DOCUMENTATION SYSTEM - DEMO")
print("="*70)

print(f"\n✓ Found demo video: {demo_video}")

# Process the video
print("\n" + "="*70)
print("STEP 1: Processing video (extracting slides)")
print("="*70)
print("\nThis may take a few minutes depending on video length...")

from video_processor import VideoProcessor

processor = VideoProcessor(demo_video, 'output')
video_id = processor.process_video()

print(f"\n✓ Video processed successfully!")
print(f"  Video ID: {video_id}")

# Show results
print("\n" + "="*70)
print("STEP 2: Review extracted slides")
print("="*70)

from database import get_video_slides

slides = get_video_slides(video_id)
print(f"\n✓ Extracted {len(slides)} slides")

for i, slide in enumerate(slides[:5], 1):  # Show first 5
    print(f"\nSlide {i}:")
    print(f"  Frame: {slide['frame_number']}")
    print(f"  Time: {slide['timestamp']:.2f}s")
    print(f"  Image: {slide['image_path']}")
    if slide['original_text']:
        print(f"  Text: {slide['original_text'][:50]}...")

if len(slides) > 5:
    print(f"\n  ... and {len(slides) - 5} more slides")

# Create sections
print("\n" + "="*70)
print("STEP 3: Create sections (optional)")
print("="*70)

from database import create_section, assign_slide_to_section

# Create two demo sections
section_a = create_section(video_id, "Section A - Introduction", 0)
section_b = create_section(video_id, "Section B - Main Content", 1)

print(f"\n✓ Created sections:")
print(f"  1. Section A (ID: {section_a})")
print(f"  2. Section B (ID: {section_b})")

# Assign first half of slides to Section A, rest to Section B
mid_point = len(slides) // 2
for i, slide in enumerate(slides):
    section_id = section_a if i < mid_point else section_b
    assign_slide_to_section(slide['id'], section_id)

print(f"\n✓ Assigned {mid_point} slides to Section A")
print(f"✓ Assigned {len(slides) - mid_point} slides to Section B")

# Generate PDF
print("\n" + "="*70)
print("STEP 4: Generate PDF")
print("="*70)

from pdf_generator_improved import generate_pdf_from_video_id

output_pdf = f'output/demo_video_{video_id}.pdf'
generate_pdf_from_video_id(video_id, output_pdf, "Demo Video Documentation")

print(f"\n✓ PDF generated: {output_pdf}")
print(f"  Size: {os.path.getsize(output_pdf) / 1024:.1f} KB")

# Summary
print("\n" + "="*70)
print("DEMO COMPLETE!")
print("="*70)

print(f"""
✅ Successfully processed demo video!

Results:
  - Video ID: {video_id}
  - Slides extracted: {len(slides)}
  - Sections created: 2
  - PDF generated: {output_pdf}

Next steps:
  1. Open {output_pdf} to view the generated documentation
  2. Run the Flask web app to edit text: python app.py
  3. Navigate to http://localhost:5000/video/{video_id} to edit
  4. Lock text and regenerate PDF for final output

For web interface:
  python app.py
  Then open: http://localhost:5000
""")
