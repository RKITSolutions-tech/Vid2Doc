#!/usr/bin/env python
"""Moved demo script into scripts/ and updated imports to use `vid2doc` package."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../')

demo_video = 'videos/demo_video.mp4'
if not os.path.exists(demo_video):
    print(f"❌ Demo video not found at: {demo_video}")
    sys.exit(1)

from vid2doc.video_processor import VideoProcessor
from vid2doc.database import get_video_slides, create_section, assign_slide_to_section
from vid2doc.pdf_generator_improved import generate_pdf_from_video_id

processor = VideoProcessor(demo_video, 'output')
video_id = processor.process_video()
slides = get_video_slides(video_id)
output_pdf = f'output/demo_video_{video_id}.pdf'
generate_pdf_from_video_id(video_id, output_pdf, "Demo Video Documentation")
print(f"Generated {output_pdf}")
