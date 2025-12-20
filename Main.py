

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

logging.info(f"Resized Video Path: {Resize_video_full_path}")

new_fps = original_fps//10
logging.info(f"New FPS: {new_fps}")

# Check if the resized video already exists
if not os.path.exists(Resize_video_full_path):
    logging.info("Resized video not found. Resizing the video...")
    resize_video(full_video_path, Resize_video_full_path, original_fps,new_fps)
else:
    logging.info("Resized video already exists. Skipping resizing.")


full_video_path=Resize_video_full_path

# Get file size
file_size = os.path.getsize(full_video_path)


# Log video properties
logging.info(f"File Size: {video_properties['file_size'] / (1024 * 1024):.2f} MB")
logging.info(f"Bit Rate: {video_properties['bit_rate'] / 1000:.2f} kbps")
logging.info(f"Aspect Ratio: {video_properties['aspect_ratio']:.2f}")
logging.info(f"Frame Rate: {video_properties['fps']:.2f} fps")
logging.info(f"Total Frames: {video_properties['frame_count']}")
logging.info(f"Duration: {video_properties['duration']:.2f} seconds")
logging.info(f"Resolution: {video_properties['width']}x{video_properties['height']}")




# Initial setup
ret, prev_frame = cap.read()  # Read the first frame
threshold1 = 0.9  # Set a similarity threshold for detecting a slide change
threshold2 = 0.9  # Set a similarity threshold for detecting a slide change
slide_changes = []  # Store timestamps of slide changes

# Initialize variables
frame_idx = 1
last_frame_idx = 1
frame_log_limit = 200  # Log progress every n frames

frame_gap = 10
transition_limit = 3
transition_counter = 1
slide_change = False




extract_video_and_audio(full_video_path,frame_gap)





c = canvas.Canvas(output_pdf_path, pagesize=letter)
width, height = letter

# Add title page
c.setFont("Helvetica-Bold", 24)
c.drawCentredString(width / 2.0, height / 2.0, "Video Slide Detection Report")
c.setFont("Helvetica", 18)
c.drawCentredString(width / 2.0, height / 2.0 - 40, f"Video: {video_file_name}")
c.showPage()  # Move to the next page

y_position = height - 120


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Compare the current frame with the previous one
    similarity_score = frame_difference(prev_frame, frame)
    similarity_score2 = compare_histograms(prev_frame, frame)

    #identifies the slide change
    if similarity_score < threshold1 or similarity_score2 < threshold2:
        logging.info(f"Slide change detected at frame {frame_idx} , similarity_score: {similarity_score:.2f} , similarity_score2: {similarity_score2:.2f}")
        slide_change = True;


    if slide_change :
        if (frame_idx - last_frame_idx) > frame_gap:
            transition_counter += 1
            if transition_counter > transition_limit:
                logging.info("Slide Difference is greater than 20 frames, taking image (frame idx {} last frame idx {}) and transition complete".format(frame_idx, last_frame_idx))
                
                #REset the slide change
                slide_change = False
                transition_counter = 1
                

                

                # A significant change has occurred, marking a slide change
                timestamp = frame_idx / fps  # Time in seconds
                slide_changes.append(timestamp)

                # Save the frame image to a temporary file
                frame_file = f"slide_{frame_idx}.jpg"
                cv2.imwrite(frame_file, frame)

                # Add the frame and timestamp to the Word document
                #doc.add_paragraph(f"Slide change at {timestamp:.2f} seconds")
                        # Add the frame image to the PDF
                c.drawImage(frame_file, 100, y_position - 150, width=5*inch, preserveAspectRatio=True, mask='auto')
                y_position -= 160

                # Add the timestamp
                c.drawString(100, y_position, f"Slide change at {timestamp:.2f} seconds")
                y_position -= 20
                #Add a capture under the image with the timestamp
                


                
                logging.info(f"Extracting text from slide {last_frame_idx} to {frame_idx} at fps {new_fps}")
                slide_text_full = get_slide_text(Resize_video_file_name,last_frame_idx,frame_idx,new_fps)
                
                word_count = len(slide_text_full.split())
                logging.info(f"Word count of the slide text: {word_count}")

                if word_count > 100 and word_count < 1000:
                    logging.info(f"Slide text has word count : {word_count} summarizing text")
                    summrise_text_result = summrise_text(slide_text_full)
                
                if word_count > 1000:
                    logging.info(f"Slide text has word count : {word_count} splitting text and summarizing")
                    # Split the slide_text_full into two halves
                    words = slide_text_full.split()
                    mid_index = len(words) // 2

                    # Find the nearest word to the middle
                    while mid_index < len(words) and not words[mid_index].endswith('.'):
                        mid_index += 1

                    first_half = ' '.join(words[:mid_index])
                    second_half = ' '.join(words[mid_index:])

                    summrise_text_result = summrise_text(first_half)[0].get("summary_text", "No summary available") + " " + summrise_text(second_half)[0].get("summary_text", "No summary available")

                else:
                    logging.info(f"Slide text has word count :  {word_count} skipping summarization")
                    summrise_text_result = {"summary_text": slide_text_full}
                
                
                # Handle the summary result based on its type
                if isinstance(summrise_text_result, dict) and 'summary_text' in summrise_text_result:
                    summary_paragraph = summrise_text_result['summary_text']
                elif isinstance(summrise_text_result, list) and len(summrise_text_result) > 0:
                    summary_paragraph = summrise_text_result[0].get("summary_text", "No summary available")
                else:
                    summary_paragraph = "No summary available"
                
                
                # Add the summary text
                c.drawString(100, y_position, f"Summary: {summary_paragraph}")
                y_position -= 20



                # Check if we need to add a new page
                if y_position < 100:
                    c.showPage()
                    y_position = height - 60

                #reset the last frame index to current index
                last_frame_idx = frame_idx


                # Clean up the saved frame image
                os.remove(frame_file)

    # Log progress every n frames
    if frame_idx % frame_log_limit == 0:
        logging.info(f" ------ Processed {frame_idx}/{total_frames} frames -------")

    # Update the previous frame
    prev_frame = frame.copy()
    frame_idx += 1





# Save the document
c.save()

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
