"""Test Katna integration"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_katna_processor_imports():
    """Test that katna_processor module can be imported"""
    from katna_processor import KatnaKeyframeExtractor, extract_keyframes_katna
    
    assert KatnaKeyframeExtractor is not None
    assert extract_keyframes_katna is not None
    assert hasattr(KatnaKeyframeExtractor, 'extract_keyframes')


def test_video_processor_has_katna_method():
    """Test that VideoProcessor has the _process_video_katna method"""
    try:
        from vid2doc.video_processor import VideoProcessor
    except ImportError as e:
        pytest.skip(f"Skipping test due to missing dependencies: {e}")
    
    # Create a dummy instance
    processor = VideoProcessor('dummy.mp4')
    
    # Check that the method exists
    assert hasattr(processor, '_process_video_katna')
    assert callable(getattr(processor, '_process_video_katna'))


def test_settings_parsing_default_method():
    """Test that settings parser handles default extraction method"""
    # Simulate the _parse_settings function
    test_settings = {
        'extraction_method': 'default',
        'threshold_ssim': 0.85,
        'frame_gap': 15,
    }
    
    def _cast(key, cast_type, default):
        value = test_settings.get(key, default)
        try:
            return cast_type(value)
        except (TypeError, ValueError):
            return default
    
    parsed = {
        'extraction_method': test_settings.get('extraction_method', 'default'),
        'threshold_ssim': _cast('threshold_ssim', float, 0.9),
        'frame_gap': _cast('frame_gap', int, 10),
        'katna_max_keyframes': _cast('katna_max_keyframes', int, 0),
    }
    
    assert parsed['extraction_method'] == 'default'
    assert parsed['threshold_ssim'] == 0.85
    assert parsed['frame_gap'] == 15
    assert parsed['katna_max_keyframes'] == 0


def test_settings_parsing_katna_method():
    """Test that settings parser handles Katna extraction method"""
    test_settings = {
        'extraction_method': 'katna',
        'katna_max_keyframes': 30,
    }
    
    def _cast(key, cast_type, default):
        value = test_settings.get(key, default)
        try:
            return cast_type(value)
        except (TypeError, ValueError):
            return default
    
    parsed = {
        'extraction_method': test_settings.get('extraction_method', 'default'),
        'katna_max_keyframes': _cast('katna_max_keyframes', int, 0),
    }
    
    assert parsed['extraction_method'] == 'katna'
    assert parsed['katna_max_keyframes'] == 30


def test_katna_extractor_initialization():
    """Test KatnaKeyframeExtractor initialization"""
    from katna_processor import KatnaKeyframeExtractor
    
    extractor = KatnaKeyframeExtractor('test_video.mp4')
    
    assert extractor.video_path == 'test_video.mp4'
    assert extractor.temp_dir is None


def test_katna_not_available_handling():
    """Test that code handles Katna not being available gracefully"""
    # This test ensures the code has proper try/except for Katna imports
    try:
        from katna_processor import extract_keyframes_katna
        # If Katna is installed, the function should exist
        assert callable(extract_keyframes_katna)
    except ImportError as e:
        # If Katna is not installed, we should get a helpful error
        assert 'Katna' in str(e) or 'katna_processor' in str(e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
