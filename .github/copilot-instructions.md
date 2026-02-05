# Copilot Instructions for Video Documentation System

## IMPORTANT: Development Approach

**DO NOT USE `fab_app.py` OR FLASK-APPBUILDER** - This file is deprecated and not part of the core solution. All changes and new features must be implemented in the core Flask application (`app.py`). The core app provides a clean, maintainable web interface without the complexity of Flask-AppBuilder.

## Project Overview

This is a Flask-based web application that automatically generates documentation from video files by extracting key slides/frames and transcribing audio to text using AI (Whisper).

## Tech Stack

- **Backend**: Flask 3.0.0 (Python 3.12+)
- **Database**: SQLite with 4 tables (videos, slides, text_extracts, sections)
- **Video Processing**: OpenCV, FFmpeg, moviepy
- **AI/ML**: OpenAI Whisper for audio transcription, transformers for text generation
- **PDF Generation**: ReportLab
- **Testing**: pytest

## Code Organization

- `app.py` - Flask web application with routes and endpoints
- `database.py` - SQLite database operations (CRUD for videos, slides, sections, text)
- `video_processor.py` - OOP design for video processing logic
- `video_processing.py` - Utility functions for video frame extraction
- `video_audio_extraction.py` - Audio extraction and transcription with Whisper
- `pdf_generator_improved.py` - PDF generation with professional two-column layout
- `templates/` - Jinja2 HTML templates for web interface
- `test_*.py` - Comprehensive test suites

## Coding Standards

### Python Style
- Follow PEP 8 conventions
- Use descriptive variable names
- Keep functions focused and under 50 lines when possible
- Add docstrings for all functions and classes
- Use type hints where appropriate

### Flask Conventions
- Use Flask blueprints for larger features (though current app is single-file)
- Configure via `app.config` dictionary
- Return proper HTTP status codes (200, 400, 404, 500)
- Handle errors gracefully with try-except blocks

### Database Operations
- Use parameterized queries to prevent SQL injection
- Always close database connections (use context managers)
- Database path: `video_documentation.db`
- Tables: videos, slides, text_extracts, sections

### Video Processing
- Supported formats: MP4, AVI, MOV, MKV
- Default thresholds for slide detection: 0.9 (adjustable)
- Extract frames at 10 FPS for slide detection
- Use OpenCV for image processing

### Testing
- Write tests for new features
- Use pytest framework
- Tests should be independent and repeatable
- Include integration tests for end-to-end workflows
- Mock external dependencies (Whisper API) when appropriate

## File Management

- Uploads go to `uploads/` directory
- Processed output goes to `output/` directory
- Max upload size: 500MB
- Clean up temporary files after processing

## Key Features to Preserve

- Slide detection using histogram comparison
- Audio transcription with Whisper AI
- Text editing interface with lock mechanism
- Section/chapter organization
- Professional PDF export with images on left, text on right
- SQLite database for persistence

## Common Tasks

### Adding New Routes
Place new Flask routes in `app.py` with proper decorators and error handling.

### Modifying Slide Detection
Adjust thresholds in `video_processor.py`:
- `threshold1` - Similarity threshold for slide detection
- `threshold2` - Histogram threshold
- `frame_gap` - Minimum frames between slide changes
- `transition_limit` - Confirmation frames for slide change

### Database Schema Changes
1. Update schema in `database.py`
2. Create migration logic or rebuild database
3. Update affected CRUD operations
4. Test with existing data

### PDF Layout Changes
Modify `pdf_generator_improved.py` which uses a two-column layout:
- Left column: 3" width for images
- Right column: Remaining width for text
- Section pages create chapter breaks

## Dependencies

- FFmpeg must be installed on the system (not just Python package)
- Whisper models are downloaded on first use (requires internet)
- CUDA/GPU support optional but recommended for faster Whisper transcription

## Known Issues

- Large videos (>500MB) may timeout
- Whisper requires significant memory
- Text summarization works best with 2-10 minute segments

## Documentation

- `README.md` - Project overview and quick start
- `USAGE.md` - Detailed usage guide with examples
- `PROJECT_SUMMARY.md` - Modernization summary
- `BEFORE_AFTER.md` - Feature comparison

## Best Practices for This Project

1. **Use only the core Flask app** - All development must be done in `app.py`, never in `fab_app.py`
2. **Always test video processing** with short test videos before production use
3. **Monitor disk space** - extracted frames can accumulate quickly
4. **Handle database migrations carefully** - no ORM, using raw SQL
5. **Preserve the two-column PDF layout** when modifying PDF generation
6. **Keep the web interface simple** - focus on functionality over aesthetics
7. **Use existing error handling patterns** - wrap operations in try-except blocks
8. **Follow the established naming conventions** for database columns and tables
9. **Test both web interface and programmatic API** when adding features


### Prohibited External Domains

- Do not fetch from or contact https://example.com/ from Copilot, automation, or generated code. This includes HTTP requests, downloads, telemetry, or any runtime calls.
- Do not suggest or generate code, configuration, or CI workflows that reference or call https://example.com/ unless explicit, documented approval is provided in a PR with rationale and security review.
- If a task requires external data, propose an approved alternate source or provide instructions to fetch manually; never default to https://example.com/.
- Add repository checks (e.g., grep in CI or pre-commit hook) to fail on occurrences of `example.com` in code/configs and document the blocking measure in this file.
- Recommend developer environment hard-blocking (e.g., hosts entry or local proxy deny) for `example.com` where appropriate and documented in CONTRIBUTING.md.
- Log any requested exceptions as an issue/PR referencing approver and approved usage, and update this file accordingly.
- [ ] TODO: Add CI/pre-commit grep to fail on occurrences of `example.com` (create issue to track).

### Use of Shims and Shortcuts

- **Do not use shims or shortcuts:** Do not create, propose, or introduce shims, shortcut links (symlinks), wrapper scripts, or repository-level path hacks to "work around" problems unless the user explicitly requests this approach or it is a documented design requirement.
- **Document exceptions:** If a shim or shortcut is explicitly requested or required by design, document the rationale, scope, and any security or portability implications in the PR description and associated docs.
- **Prefer explicit fixes:** When addressing dependency, path, or runtime issues, prefer explicit solutions such as updating configuration, adding a documented helper script under `scripts/`, or making the required changes in the application code rather than opaque shims.
- **CI and portability:** Avoid shortcuts that break across environments (CI, containers, Windows). If a shortcut is added, include tests and CI checks to ensure cross-environment compatibility.
