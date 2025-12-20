#!/usr/bin/env python
"""
Example script demonstrating dual-resolution video processing.

This script shows how to use the new dual-resolution feature to process
videos quickly while maintaining high-quality output.
"""

import sys
import os

# Add the project root to path if running from examples directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_processor import VideoProcessor


def process_video_fast_quality(video_path, output_dir='output'):
    """
    Process video with optimal settings for speed and quality.
    
    Uses:
    - 25% processing resolution for fast slide detection
    - 100% target resolution for high-quality images
    
    This provides approximately 16x faster processing while maintaining
    full image quality in the output.
    """
    print("=" * 60)
    print("Dual-Resolution Video Processing Example")
    print("=" * 60)
    print(f"\nVideo: {video_path}")
    print(f"Output: {output_dir}\n")
    
    # Configure settings for fast processing with quality output
    settings = {
        # Slide detection thresholds
        'threshold_ssim': 0.9,
        'threshold_hist': 0.9,
        
        # Frame gap and transition confirmation
        'frame_gap': 10,
        'transition_limit': 3,
        
        # NEW: Dual-resolution settings
        'scale_percent': 25,  # Use 25% resolution for fast processing
        'target_resolution_percent': 100,  # Save images at full quality
        
        # Other settings
        'histogram_bins': 256,
        'whisper_model': 'base',
        'progress_interval': 50,
    }
    
    print("Settings:")
    print(f"  Processing Resolution: {settings['scale_percent']}%")
    print(f"  Target Image Resolution: {settings['target_resolution_percent']}%")
    print(f"  Expected speedup: ~16x")
    print()
    
    # Create processor and process video
    processor = VideoProcessor(video_path, output_dir)
    
    def progress_callback(event):
        """Simple progress callback to show processing status"""
        event_type = event.get('type')
        
        if event_type == 'started':
            print(f"Started processing video ID: {event.get('video_id')}")
            print(f"Total frames: {event.get('total_frames')}")
            print(f"FPS: {event.get('fps')}\n")
        
        elif event_type == 'progress':
            percent = event.get('percent_complete', 0)
            frames = event.get('frames_processed', 0)
            total = event.get('total_frames', 0)
            print(f"Progress: {percent:.1f}% ({frames}/{total} frames)", end='\r')
        
        elif event_type == 'slide':
            frame = event.get('frame')
            timestamp = event.get('timestamp', 0)
            print(f"\nSlide captured at frame {frame} ({timestamp:.2f}s)")
        
        elif event_type == 'complete':
            video_id = event.get('video_id')
            print(f"\n\n✅ Processing complete! Video ID: {video_id}")
    
    try:
        video_id = processor.process_video(
            settings=settings,
            progress_callback=progress_callback
        )
        
        if video_id:
            print(f"\nSuccess! Video processed with ID: {video_id}")
            print(f"Slides saved to: {output_dir}")
            return video_id
        else:
            print("\n❌ Processing failed")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_processing_speeds(video_path, output_dir='output'):
    """
    Demonstrate the speed difference between different processing resolutions.
    
    Note: This is just an example. In production, you would only process once
    with your preferred settings.
    """
    import time
    
    print("\n" + "=" * 60)
    print("Processing Speed Comparison")
    print("=" * 60)
    
    test_configs = [
        {'name': 'Full Resolution', 'scale_percent': 100, 'target_resolution_percent': 100},
        {'name': 'Fast Processing', 'scale_percent': 25, 'target_resolution_percent': 100},
        {'name': 'Very Fast', 'scale_percent': 10, 'target_resolution_percent': 100},
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\nTesting: {config['name']}")
        print(f"  Processing: {config['scale_percent']}%")
        print(f"  Target: {config['target_resolution_percent']}%")
        
        settings = {
            'threshold_ssim': 0.9,
            'threshold_hist': 0.9,
            'frame_gap': 10,
            'transition_limit': 3,
            'scale_percent': config['scale_percent'],
            'target_resolution_percent': config['target_resolution_percent'],
            'whisper_model': 'base',
            'min_slide_audio_seconds': 0.0,
            'min_slide_audio_seconds': 0.0,
        }
        
        processor = VideoProcessor(video_path, output_dir)
        
        start_time = time.time()
        try:
            video_id = processor.process_video(settings=settings)
            elapsed = time.time() - start_time
            
            results.append({
                'name': config['name'],
                'time': elapsed,
                'video_id': video_id
            })
            
            print(f"  ✅ Completed in {elapsed:.2f}s")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    # Print comparison
    if results:
        print("\n" + "=" * 60)
        print("Results Summary")
        print("=" * 60)
        baseline = results[0]['time'] if results else 1
        
        for result in results:
            speedup = baseline / result['time'] if result['time'] > 0 else 0
            print(f"{result['name']:20} | {result['time']:8.2f}s | {speedup:.1f}x")


if __name__ == '__main__':
    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python example_dual_resolution.py <video_path> [output_dir]")
        print("\nExample:")
        print("  python example_dual_resolution.py videos/demo_video.mp4")
        print("  python example_dual_resolution.py videos/demo_video.mp4 output/demo")
        sys.exit(1)
    
    video_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    
    if not os.path.exists(video_path):
        print(f"❌ Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Process the video with optimal dual-resolution settings
    process_video_fast_quality(video_path, output_dir)
    
    # Optional: Uncomment to run speed comparison
    # compare_processing_speeds(video_path, output_dir)
