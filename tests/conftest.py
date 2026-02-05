import tempfile
import os
import shutil
import sys
import pytest

# Ensure repository root is on sys.path so local modules import correctly during pytest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def use_temp_db(tmp_path, monkeypatch):
    """Create a temporary sqlite DB file for tests and initialize schema."""
    db_file = tmp_path / "test_video_documentation.db"
    
    # Set environment variable for the test database
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', f'sqlite:///{db_file}')
    
    # Import and reinitialize the engine with the test database
    from vid2doc.models_sqlalchemy import reinit_engine, init_models
    reinit_engine(f'sqlite:///{db_file}')
    
    # Initialize schema
    init_models()
    yield
    # cleanup if needed
    try:
        if db_file.exists():
            db_file.unlink()
    except Exception:
        pass


@pytest.fixture
def db_session():
    """Provide a SQLAlchemy session for tests."""
    from vid2doc.models_sqlalchemy import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def resolve_video_path(synthetic_video_path):
    """Return path to demo video if present in repo, otherwise the synthetic one."""
    repo_video = os.path.join(os.getcwd(), 'videos', 'small_demo_video.mp4')
    if os.path.exists(repo_video):
        return repo_video
    return synthetic_video_path
