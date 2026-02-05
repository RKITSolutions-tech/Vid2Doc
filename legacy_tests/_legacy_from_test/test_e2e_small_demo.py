import os
import time
import shutil
import pytest
from pathlib import Path


TEST_VIDEO = 'videos/small_demo_video.mp4'


@pytest.mark.skipif(not os.path.exists(TEST_VIDEO), reason="small_demo_video.mp4 not present")
def test_e2e_process_and_pdf(tmp_path):
    outdir = tmp_path / 'out'
    outdir.mkdir()
    test_db = tmp_path / 'test_e2e.db'

    # Ensure test DB is used by modules that read DATABASE_PATH
    os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{str(test_db)}'

    # Initialize DB
    from database import init_db
    # Override database path for sqlite helper
    import database
    database.DATABASE_PATH = str(test_db)
    init_db()

    # Initialize SQLAlchemy models to point to the test DB (used by PDF generator)
    try:
        from models_sqlalchemy import reinit_engine, init_models
        # Reinit engine to use the SQLALCHEMY_DATABASE_URI we set above
        reinit_engine(os.environ['SQLALCHEMY_DATABASE_URI'])
        init_models()
    except Exception as e:
        # If SQLAlchemy models can't be initialized, continue and let PDF generator raise
        print('Warning: init_models failed:', e)

    # Prepare a persistent test_output folder for logs/artifacts
    repo_out = Path('test_output')
    repo_out.mkdir(exist_ok=True)

    # Process video
    from vid2doc.video_processor import VideoProcessor

    processor = VideoProcessor(TEST_VIDEO, str(outdir))

    start_time = time.time()
    video_id = processor.process_video()
    end_time = time.time()

    assert video_id is not None, 'Video processing returned no id'

    elapsed = end_time - start_time
    print(f'Processing start: {start_time}, end: {end_time}, elapsed: {elapsed:.2f}s')

    # (defer persistence until after slides are available)

    # Verify slides in DB
    from database import get_video_slides
    slides = get_video_slides(video_id)
    assert slides and len(slides) > 0, 'No slides extracted'

    # Print slide timestamps for inspection
    timestamps = [s['timestamp'] for s in slides]
    print('Extracted slide timestamps (s):', timestamps)

    # Generate PDF
    from pdf_generator_improved import generate_pdf_from_video_id
    pdf_path = str(outdir / 'e2e_output.pdf')
    generate_pdf_from_video_id(video_id, pdf_path, 'E2E Small Demo')

    assert os.path.exists(pdf_path), 'PDF not created'
    assert os.path.getsize(pdf_path) > 0, 'PDF is empty'

    # Persist run metadata to test_output with a timestamped filename
    import json
    pdf_size_kb = os.path.getsize(pdf_path) / 1024.0 if os.path.exists(pdf_path) else 0
    run_meta = {
        'video': TEST_VIDEO,
        'video_id': video_id,
        'start_time': start_time,
        'end_time': end_time,
        'elapsed_seconds': elapsed,
        'slide_count': len(slides),
        'slide_timestamps': timestamps,
        'pdf_path': pdf_path,
        'pdf_size_kb': pdf_size_kb,
    }
    ts_label = int(start_time)
    json_path = repo_out / f'e2e_run_{ts_label}.json'
    txt_path = repo_out / f'e2e_run_{ts_label}.log'
    with open(json_path, 'w', encoding='utf8') as jf:
        json.dump(run_meta, jf, indent=2)
    with open(txt_path, 'w', encoding='utf8') as tf:
        tf.write(f"E2E run for {TEST_VIDEO}\n")
        tf.write(f"Start: {start_time}\nEnd: {end_time}\nElapsed: {elapsed:.2f}s\n")
        tf.write(f"Video ID: {video_id}\nSlides: {len(slides)}\nTimestamps: {timestamps}\n")
        tf.write(f"PDF: {pdf_path} ({pdf_size_kb:.1f} KB)\n")

    # Cleanup artifacts
    try:
        if os.path.exists(str(outdir)):
            shutil.rmtree(str(outdir))
        if os.path.exists(str(test_db)):
            os.remove(str(test_db))
    except Exception:
        pass
