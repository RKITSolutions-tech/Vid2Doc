

import os
import logging

import time
from  video_audio_extraction import get_slide_text,summrise_text
from video_processing import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load the video
video_path = "videos"
video_file_name = "Day 01 Part 01-Clip.mp4"
video_file_name_no_ext = os.path.splitext(video_file_name)[0]

output_pdf_path = "output/"+ video_file_name_no_ext + ".pdf"

full_video_path=os.path.join(video_path , video_file_name)
logging.info(f"Video Path: {full_video_path}")


# Record the start time
start_time = time.time()


# Get video properties
video_properties = get_video_properties(full_video_path)

# Get the FPS from the original video
original_fps = video_properties['fps']


Resize_video_file_name = video_file_name_no_ext+'-s.mp4'
Resize_video_full_path=os.path.join(video_path , Resize_video_file_name)
"""Deprecated root module.

This module has been moved into the `scripts/` directory and the
`vid2doc` package. Use the `scripts/Main.py` wrapper or import from
the package instead.
"""
raise ImportError("Main functionality moved: use scripts/Main.py or import from 'vid2doc' package")
# Release the video capture object
cap.release()

# Clear all the WAV files created from the process
wav_files = [f for f in os.listdir(video_path) if f.endswith('.wav')]
for wav_file in wav_files:
    wav_file_path = os.path.join(video_path, wav_file)
    os.remove(wav_file_path)
    logging.info(f"Deleted WAV file: {wav_file_path}")


# Record the end time
end_time = time.time()

# Calculate and print the total processing time
total_processing_time = end_time - start_time
logging.info(f"Total processing time: {total_processing_time:.2f} seconds")
