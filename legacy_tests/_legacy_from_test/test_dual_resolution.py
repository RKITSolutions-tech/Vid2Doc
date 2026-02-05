"""Test dual-resolution video processing"""
import pytest
import os
import tempfile
import cv2
import numpy as np
from vid2doc.video_processor import VideoProcessor
from unittest.mock import patch


def create_test_video(path, duration_sec=2, fps=10, width=640, height=480):
    """Create a simple test video with distinct frames"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    
    total_frames = int(duration_sec * fps)
    
    for i in range(total_frames):
        # Create frames with different colors for easy slide detection
        if i < total_frames // 2:
            # First half: red frames
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 2] = 200  # Red channel
        else:
            # Second half: blue frames (should trigger slide change)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = 200  # Blue channel
        
        writer.write(frame)
    
    writer.release()


class TestDualResolution:
    """Test dual-resolution processing"""
    
    def test_processing_and_target_resolution_independent(self):
        """
        Test that processing resolution and target resolution work independently.
        
        - Processing resolution affects comparison speed
        - Target resolution affects saved image quality
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, 'test_video.mp4')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create test video
            create_test_video(video_path, duration_sec=2, fps=10, width=640, height=480)
            
            # Mock audio extraction to speed up test
            def fake_get_slide_text(filename, start_frame, end_frame, fps, model_size="base"):
                return "Mock transcribed text"
            
            def fake_summrise_text(text, min_length=30, max_length=150, model_name="mock-model"):
                return [{"summary_text": "Mock summary"}]
            
            settings = {
                "threshold_ssim": 0.9,
                "threshold_hist": 0.9,
                "frame_gap": 3,
                "transition_limit": 1,
                "scale_percent": 25,  # Very low processing resolution for speed
                "target_resolution_percent": 80,  # Different target resolution for saved images
                "min_slide_audio_seconds": 0.0,
            }
            
              with patch("vid2doc.video_audio_extraction.get_slide_text", side_effect=fake_get_slide_text), \
                  patch("vid2doc.video_audio_extraction.summrise_text", side_effect=fake_summrise_text):
                processor = VideoProcessor(video_path, output_dir)
                video_id = processor.process_video(settings=settings)
            
            assert video_id is not None, "Video processing should complete successfully"
            
            # Check that slide images were created
            slide_files = [f for f in os.listdir(output_dir) if f.startswith('slide_')]
            assert len(slide_files) >= 2, "Should detect at least 2 slides (color change)"
            
            # Verify saved images have expected dimensions (80% of original)
            for slide_file in slide_files:
                slide_path = os.path.join(output_dir, slide_file)
                img = cv2.imread(slide_path)
                assert img is not None, f"Should be able to read saved slide: {slide_file}"
                
                height, width = img.shape[:2]
                # Target resolution is 80% of 640x480 = 512x384
                expected_width = int(640 * 0.8)
                expected_height = int(480 * 0.8)
                
                # Allow small tolerance due to rounding
                assert abs(width - expected_width) <= 2, f"Width should be ~{expected_width}, got {width}"
                assert abs(height - expected_height) <= 2, f"Height should be ~{expected_height}, got {height}"
    
    def test_very_low_processing_resolution(self):
        """
        Test that very low processing resolution (10%) works without errors.
        
        This ensures fast processing for large videos.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, 'test_video.mp4')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create test video
            create_test_video(video_path, duration_sec=1, fps=5, width=1920, height=1080)
            
            # Mock audio extraction
            def fake_get_slide_text(filename, start_frame, end_frame, fps, model_size="base"):
                return "Mock text"
            
            def fake_summrise_text(text, min_length=30, max_length=150, model_name="mock-model"):
                return [{"summary_text": "Mock summary"}]
            
            settings = {
                "threshold_ssim": 0.9,
                "threshold_hist": 0.9,
                "frame_gap": 2,
                "transition_limit": 1,
                "scale_percent": 10,  # Very low processing resolution
                "target_resolution_percent": 100,  # Full resolution for saved images
                "min_slide_audio_seconds": 0.0,
            }
            
              with patch("vid2doc.video_audio_extraction.get_slide_text", side_effect=fake_get_slide_text), \
                  patch("vid2doc.video_audio_extraction.summrise_text", side_effect=fake_summrise_text):
                processor = VideoProcessor(video_path, output_dir)
                video_id = processor.process_video(settings=settings)
            
            assert video_id is not None, "Should process successfully with 10% scale"
            
            # Check saved images maintain full resolution
            slide_files = [f for f in os.listdir(output_dir) if f.startswith('slide_')]
            assert len(slide_files) >= 1, "Should save at least one slide"
            
            for slide_file in slide_files:
                slide_path = os.path.join(output_dir, slide_file)
                img = cv2.imread(slide_path)
                height, width = img.shape[:2]
                
                # Images should be at full resolution (1920x1080)
                assert width == 1920, f"Width should be 1920, got {width}"
                assert height == 1080, f"Height should be 1080, got {height}"
    
    def test_default_behavior_unchanged(self):
        """
        Test that default behavior (100% for both) is unchanged.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, 'test_video.mp4')
            output_dir = os.path.join(temp_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create test video
            create_test_video(video_path, duration_sec=1, fps=5, width=320, height=240)
            
            # Mock audio extraction
            def fake_get_slide_text(filename, start_frame, end_frame, fps, model_size="base"):
                return "Mock text"
            
            def fake_summrise_text(text, min_length=30, max_length=150, model_name="mock-model"):
                return [{"summary_text": "Mock summary"}]
            
            # Use defaults (no scale_percent or target_resolution_percent specified)
            settings = {
                "threshold_ssim": 0.9,
                "threshold_hist": 0.9,
                "frame_gap": 2,
                "transition_limit": 1,
                "min_slide_audio_seconds": 0.0,
            }
            
              with patch("vid2doc.video_audio_extraction.get_slide_text", side_effect=fake_get_slide_text), \
                  patch("vid2doc.video_audio_extraction.summrise_text", side_effect=fake_summrise_text):
                processor = VideoProcessor(video_path, output_dir)
                video_id = processor.process_video(settings=settings)
            
            assert video_id is not None, "Should process with default settings"
            
            # Check saved images maintain original resolution
            slide_files = [f for f in os.listdir(output_dir) if f.startswith('slide_')]
            for slide_file in slide_files:
                slide_path = os.path.join(output_dir, slide_file)
                img = cv2.imread(slide_path)
                height, width = img.shape[:2]
                
                # Images should be at original resolution
                assert width == 320, f"Width should be 320, got {width}"
                assert height == 240, f"Height should be 240, got {height}"
