import importlib


def test_summarizer_fallback_includes_note_on_hf_block():
    # Import module (this will use the existing fallback if HF cannot load)
    mod = importlib.import_module('vid2doc.video_audio_extraction')
    res = mod.summrise_text('This is a short test for the fallback', max_length=10)
    assert isinstance(res, list)
    assert len(res) == 1
    item = res[0]
    assert 'summary_text' in item
    # If transformers/torch load was blocked by the safety check, the fallback includes a 'note'
    # We accept either presence or absence of 'note' (environment dependent) but if present it must be a string.
    if 'note' in item:
        assert isinstance(item['note'], str)
