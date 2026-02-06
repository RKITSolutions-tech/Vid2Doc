#!/usr/bin/env python3
"""Quick test to diagnose audio extraction issues."""
import os
import sys
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

print("=" * 70)
print("AUDIO EXTRACTION DIAGNOSTIC TEST")
print("=" * 70)

# Test 1: Check if demo video exists
demo_video = 'tests/demo_video.mp4'
print(f"\n1. Checking for demo video: {demo_video}")
if os.path.exists(demo_video):
    size = os.path.getsize(demo_video)
    print(f"   ✓ Found: {demo_video} ({size:,} bytes)")
else:
    print(f"   ✗ Not found: {demo_video}")
    sys.exit(1)

# Test 2: Check required dependencies
print("\n2. Checking dependencies:")
dependencies = {
    'cv2': 'opencv-python',
    'whisper': 'openai-whisper',
    'ffmpeg': 'ffmpeg-python',
    'moviepy': 'moviepy',
}

for module, package in dependencies.items():
    try:
        __import__(module)
        print(f"   ✓ {module} (from {package})")
    except ImportError as e:
        print(f"   ✗ {module} NOT INSTALLED - install with: pip install {package}")
        print(f"      Error: {e}")

# Test 3: Check if ffmpeg binary is available
print("\n3. Checking ffmpeg binary:")
import subprocess
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print(f"   ✓ {version_line}")
    else:
        print(f"   ✗ ffmpeg failed with code {result.returncode}")
except FileNotFoundError:
    print("   ✗ ffmpeg NOT FOUND in PATH")
    print("      Install: apt-get install ffmpeg  (or brew install ffmpeg on Mac)")
except Exception as e:
    print(f"   ✗ Error checking ffmpeg: {e}")

# Test 4: Try to import and test video_processor
print("\n4. Testing video_processor import:")
try:
    from vid2doc.video_processor import VideoProcessor
    print("   ✓ VideoProcessor imported successfully")
except Exception as e:
    print(f"   ✗ Failed to import VideoProcessor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Try to get video properties
print("\n5. Testing video properties extraction:")
try:
    from vid2doc.video_processing import get_video_properties
    props = get_video_properties(demo_video)
    print(f"   ✓ Video properties:")
    print(f"      - FPS: {props.get('fps')}")
    print(f"      - Duration: {props.get('duration'):.2f}s")
    print(f"      - Frame count: {props.get('frame_count')}")
    print(f"      - Resolution: {props.get('width')}x{props.get('height')}")
except Exception as e:
    print(f"   ✗ Failed to get video properties: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Try minimal audio extraction
print("\n6. Testing audio extraction directly:")
os.makedirs('test_wav', exist_ok=True)
test_wav = 'test_wav/test_segment.wav'

try:
    from vid2doc.video_audio_extraction import extract_audio_segment
    print(f"   Attempting to extract 0-30 frames at 30fps to: {test_wav}")
    extract_audio_segment(demo_video, 0, 30, 30, test_wav, max_attempts=1)
    if os.path.exists(test_wav):
        wav_size = os.path.getsize(test_wav)
        print(f"   ✓ Audio extracted successfully! ({wav_size:,} bytes)")
    else:
        print(f"   ✗ Audio extraction completed but file not found")
except Exception as e:
    print(f"   ✗ Audio extraction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Test get_slide_text if extraction worked
if os.path.exists(test_wav):
    print("\n7. Testing Whisper transcription:")
    try:
        from vid2doc.video_audio_extraction import get_slide_text
        print("   Loading Whisper model and transcribing...")
        text = get_slide_text(demo_video, 0, 30, 30, model_size='base', video_id=999)
        print(f"   ✓ Transcription result: '{text[:100]}...'")
    except Exception as e:
        print(f"   ✗ Transcription failed: {e}")
        import traceback
        traceback.print_exc()

# Test 8: Full processor test with minimal settings
print("\n8. Testing full VideoProcessor workflow:")
try:
    import tempfile
    import shutil
    
    # Create temp output dir
    temp_output = tempfile.mkdtemp(prefix='vid2doc_test_')
    print(f"   Output directory: {temp_output}")
    
    # Initialize database in temp location
    import vid2doc.database as db
    temp_db = os.path.join(temp_output, 'test.db')
    original_db = db.DATABASE_PATH
    db.DATABASE_PATH = temp_db
    db.init_db()
    
    processor = VideoProcessor(demo_video, temp_output)
    
    # Track events
    events = []
    def progress_callback(event):
        events.append(event)
        if event.get('type') in ('status', 'error'):
            print(f"   [{event.get('type')}] {event.get('message', '')}")
    
    # Process with minimal settings
    settings = {
        'whisper_model': 'base',
        'audio_retry_attempts': 1,
        'progress_interval': 10,
        'preview_interval': 50,
        'force_slide_interval': 100,
    }
    
    print("   Starting processing...")
    video_id = processor.process_video(settings=settings, progress_callback=progress_callback)
    
    if video_id:
        print(f"   ✓ Processing completed! Video ID: {video_id}")
        
        # Check for wav files
        wav_dir = f'wav/{video_id}'
        if os.path.exists(wav_dir):
            wav_files = [f for f in os.listdir(wav_dir) if f.endswith('.wav')]
            print(f"   ✓ WAV files created: {len(wav_files)} files in {wav_dir}")
            for wf in wav_files[:3]:
                print(f"      - {wf}")
        else:
            print(f"   ✗ WAV directory not found: {wav_dir}")
        
        # Check for slides
        slides = db.get_video_slides(video_id)
        print(f"   ✓ Slides extracted: {len(slides)}")
    else:
        print("   ✗ Processing returned no video ID")
    
    # Cleanup
    db.DATABASE_PATH = original_db
    shutil.rmtree(temp_output, ignore_errors=True)
    
except Exception as e:
    print(f"   ✗ Full processing test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 70)
