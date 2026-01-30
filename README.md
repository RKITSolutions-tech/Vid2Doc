# Video Documentation System

A Flask-based web application that automatically generates documentation from video files by extracting key slides/frames and transcribing audio to text.

## Features

- **Video Upload & Processing**: Upload video files (MP4, AVI, MOV, MKV) for automatic processing
- **Dual Extraction Methods**: ⚡ NEW! Choose between traditional frame analysis or AI-powered Katna keyframe detection
  - **Default Method**: Frame-by-frame SSIM and histogram comparison with fine-tuned control
  - **Katna Method (WIP — currently not functional)**: Intelligent AI-based keyframe extraction. Integration is a work-in-progress and may not function as expected.
  - See [KATNA_INTEGRATION.md](KATNA_INTEGRATION.md) for details and current status
- **Dual-Resolution Processing**: ⚡ NEW! Process videos up to 100x faster while maintaining full output quality
  - Separate processing resolution (10-100%) for speed
  - Independent target resolution (25-100%) for quality
  - See [DUAL_RESOLUTION_FEATURE.md](DUAL_RESOLUTION_FEATURE.md) for details
- **Slide Detection**: Automatically detects slide changes in videos
- **Audio Transcription**: Extracts and transcribes audio using Whisper AI
- **Text Editing**: Edit extracted text with AI-generated suggestions
- **Section Organization**: Group slides into chapters/sections
- **Text Locking**: Lock finalized text to prevent further edits
- **PDF Export**: Generate professional PDFs with images on the left and text on the right
- **SQLite Database**: All data stored in a local database for easy management

## Installation

### Prerequisites

- Python 3.12+
- FFmpeg (for video processing)
- OpenCV (recommended). If OpenCV is not installed, the app will attempt to use the system `ffprobe` (from FFmpeg) as a fallback to gather video metadata.

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Ryan-Kenning/VideoDcumentation.git
cd VideoDcumentation
```

2. Bootstrap the project (create virtualenv, install Python deps, check system tools):
```bash
bash scripts/bootstrap.sh
# If you prefer to install system packages automatically on Debian/Ubuntu use:
# sudo apt update && sudo apt install ffmpeg
```

3. (Optional) Run an environment check to verify packages and tools:
```bash
.venv/bin/python scripts/check_env.py
```

4. Initialize the database:
```bash
python database.py
```

Health check

After bootstrapping you can verify key runtime dependencies via the web app or CLI:

- HTTP: GET /api/health will return JSON describing ffprobe and required Python packages
- CLI: `.venv/bin/python scripts/check_env.py` prints a summary and exits non-zero on missing requirements


## Usage

### Running the Web Application

Start the Flask server:
```bash
python app.py
```

Then open your browser to `http://localhost:5000`

### Workflow

1. **Upload Video**: Navigate to the Upload page and select your video file
2. **Processing**: Wait for the system to process the video (may take several minutes)
3. **Edit Text**: Review and edit the extracted text for each slide
4. **Create Sections**: Organize slides into sections/chapters
5. **Lock Text**: Lock text when finalized
6. **Export PDF**: Generate a PDF document with your documentation

### Command Line Usage

You can also use the modules programmatically:

```python
from video_processor import VideoProcessor
from pdf_generator_improved import generate_pdf_from_video_id

# Process a video with dual-resolution for speed + quality
processor = VideoProcessor('path/to/video.mp4', 'output')
settings = {
    'scale_percent': 25,  # 16x faster processing
    'target_resolution_percent': 100,  # Full quality images
}
video_id = processor.process_video(settings=settings)

# Generate PDF
generate_pdf_from_video_id(video_id, 'output.pdf', 'My Documentation')
```

For more examples, see:
- [example_dual_resolution.py](example_dual_resolution.py) - Dual-resolution processing example
- [DUAL_RESOLUTION_FEATURE.md](DUAL_RESOLUTION_FEATURE.md) - Complete feature documentation

## Devcontainer (recommended for development)

If you want a reproducible development environment (including CUDA-enabled PyTorch), use the provided devcontainer configuration.

Steps:

1. Rebuild the devcontainer in VS Code: Command Palette -> Remote-Containers: Rebuild and Reopen in Container
2. The post-create script will install micromamba, create a `dev` conda environment, install PyTorch + CUDA packages, and then install project Python dependencies into the micromamba `dev` env. It will also create a lightweight `.venv` in the project root and install a minimal set of packages so `bash start_flask.sh` can run out-of-the-box.

To activate and use the environments:

- Activate the micromamba env:

  micromamba activate dev

- Use the project's venv (created at `.venv`) for the Flask helper script:

  source .venv/bin/activate
  bash start_flask.sh full

Notes:
- The post-create step filters out `torch`/`torchvision`/`torchaudio` from `requirements.txt` because those should be installed from the PyTorch channel matching your CUDA runtime.
- You can edit `.devcontainer/post_create.sh` to tweak package versions or add more tools you need.


## Testing

The project includes a comprehensive test suite with automated smoke tests and manual tests.

### Quick Smoke Tests (Fast, Always Run)

These tests verify core functionality and run in seconds:

```bash
# Test basic functionality (database, video utilities, PDF generation)
pytest tests/test_basic.py

# Test Flask app initialization and routes
pytest tests/test_smoke_flask.py

# Test video processing pipeline end-to-end
pytest tests/test_smoke_demo.py
```

### Complete Workflow Test

This test processes the actual `small_demo_video.mp4` file and validates the complete workflow:

```bash
# Run complete end-to-end smoke test (requires small_demo_video.mp4)
pytest tests/test_smoke_workflow.py
```

This test:
- Processes `small_demo_video.mp4`
- Extracts slides
- Creates sections
- Edits slide text
- Adds document text
- Exports PDF

### Manual/Integration Tests

These tests are more comprehensive and require demo videos:

```bash
# Run all database tests
pytest -xvs tests/test_suite.py::TestDatabase

# Run video processing test (requires demo_video.mp4)
pytest -xvs tests/test_suite.py::TestVideoProcessing::test_process_demo_video

# Run text editing test
pytest -xvs tests/test_suite.py::TestTextEditing::test_edit_text_and_create_sections

# Run PDF generation test
pytest -xvs tests/test_suite.py::TestPDFGeneration::test_export_pdf

# View test instructions
python tests/test_suite.py
```

### Demo Script

Process the demo video with a complete workflow example:
```bash
python demo.py
```

## Continuous Integration

This project uses GitHub Actions for continuous integration. The CI workflow automatically runs on every push and pull request to the main branch.

### What Gets Tested

The CI workflow runs:
- **Database Tests**: All database CRUD operations (`tests/test_suite.py::TestDatabase`)
- **Basic Tests**: Core functionality verification (`tests/test_basic.py`)
- **Flask App Smoke Test**: Verifies Flask app can start and routes work (`tests/test_smoke_flask.py`)
- **Video Processing Smoke Test**: End-to-end video processing with synthetic test video (`tests/test_smoke_demo.py`)

Manual tests that require demo videos are excluded from CI and should be run locally during development.

### Complete End-to-End Smoke Test

A comprehensive smoke test workflow is available that tests the complete workflow including:
- Processing `small_demo_video.mp4`
- Creating sections
- Editing slide text
- Adding document text
- Exporting PDF

This workflow can be triggered manually from the GitHub Actions UI:

1. Go to the repository on GitHub
2. Click on the "Actions" tab
3. Select "Smoke Test Workflow" from the left sidebar
4. Click "Run workflow" button

You can also run it locally:
```bash
pytest tests/test_smoke_workflow.py
```

### Running CI Locally

To run the same tests that CI runs:

```bash
# Install dependencies
pip install -r requirements.txt

# Run all CI tests
pytest -xvs tests/test_suite.py::TestDatabase
pytest tests/test_basic.py
pytest tests/test_smoke_flask.py
pytest tests/test_smoke_demo.py
```

### CI Configuration

The CI workflow is defined in `.github/workflows/ci.yml` and includes:
- Python 3.12 setup
- FFmpeg installation
- Dependency installation with pip caching
- Automated test execution
- Timeout protection (30 minutes)

The smoke test workflow is defined in `.github/workflows/smoke-test.yml` and runs on-demand via workflow_dispatch.

## Project Structure

```
VideoDcumentation/
├── app.py                      # Flask web application
├── database.py                 # Database operations
├── video_processor.py          # Video processing logic
├── video_processing.py         # Video utility functions
├── video_audio_extraction.py   # Audio extraction and transcription
├── pdf_generator_improved.py   # PDF generation with improved layout
├── templates/                  # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── upload.html
│   └── edit_video.html
├── test/                       # Automated tests and smoke checks
│   ├── test_basic.py
│   ├── test_integration.py
│   ├── test_smoke_demo.py
│   ├── test_smoke_flask.py
│   ├── test_smoke_workflow.py
│   └── test_suite.py
├── requirements.txt            # Python dependencies
└── README.md                   # This file

Legacy files (kept for reference):
├── Main.py                     # Original script
├── pdf_generation.py           # Original PDF generator
└── Archive/                    # Archived code
```

## Database Schema

### Videos Table
- `id`: Primary key
- `filename`: Original filename
- `original_path`: Path to video file
- `upload_date`: Upload timestamp
- `duration`: Video duration in seconds
- `fps`: Frames per second
- `processed`: Processing status

### Slides Table
- `id`: Primary key
- `video_id`: Foreign key to videos
- `frame_number`: Frame number in video
- `timestamp`: Timestamp in seconds
- `image_path`: Path to extracted image
- `section_id`: Foreign key to sections (optional)

### Text Extracts Table
- `id`: Primary key
- `slide_id`: Foreign key to slides
- `original_text`: Original transcribed text
- `suggested_text`: AI-suggested summary
- `final_text`: User-edited final text
- `is_locked`: Lock status
- `created_at`: Creation timestamp
- `updated_at`: Update timestamp

### Sections Table
- `id`: Primary key
- `video_id`: Foreign key to videos
- `title`: Section title
- `order_index`: Display order
- `created_at`: Creation timestamp

## API Endpoints

### Web Pages
- `GET /` - Home page
- `GET /upload` - Upload page
- `POST /upload` - Upload and process video
- `GET /video/<video_id>` - Edit video page
- `GET /export/<video_id>` - Export video to PDF

### API Endpoints
- `POST /api/update_text/<slide_id>` - Update text for a slide
- `POST /api/create_section/<video_id>` - Create a new section
- `POST /api/assign_to_section/<slide_id>` - Assign slide to section

## Configuration

Edit configuration in `app.py`:
- `UPLOAD_FOLDER`: Where uploaded videos are stored (default: 'uploads')
- `OUTPUT_FOLDER`: Where output files are stored (default: 'output')
- `MAX_CONTENT_LENGTH`: Maximum upload size (default: 500MB)

## Known Issues & Limitations

1. Large videos may take a long time to process
2. The Whisper model requires significant memory
3. Text summarization may not work well for very short or very long segments
4. PDF generation requires images to exist on disk
5. The Katna keyframe extraction integration is currently not working and is marked as work in progress; avoid relying on Katna until the integration is fixed.

## Future Improvements

See the issue tracker for planned enhancements including:
- Better progress indicators during processing
- Support for more video formats
- Improved text summarization
- Batch processing
- Export to multiple formats (Word, HTML)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses

This project includes or optionally uses several third-party libraries:

**Core Dependencies (Always Used):**
- Flask (BSD-3-Clause)
- OpenCV (Apache 2.0)
- Whisper AI (MIT)
- PyTorch (BSD-3-Clause)
- Transformers (Apache 2.0)
- ReportLab (BSD)
- MoviePy (MIT)

**Optional Dependencies:**
- **Katna (GPL-3.0)**: If you enable the Katna keyframe extraction method (optional feature), 
  note that Katna is licensed under GPL-3.0. Your use of the Katna extraction features will 
  be subject to GPL-3.0 license terms. The core application works fully without Katna.

**System Requirements:**
- **FFmpeg**: Required for video processing. FFmpeg is licensed under LGPL 2.1+ or GPL 2+ 
  depending on build configuration. See https://ffmpeg.org/legal.html

For a complete list of dependency licenses, run:
```bash
pip install pip-licenses
pip-licenses --format=markdown --with-urls > THIRD_PARTY_LICENSES.md
```

## Contributing

Contributions are welcome! Please see the issue tracker for areas that need work.
