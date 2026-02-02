# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details

"""Database module for managing video documentation data"""
import sqlite3
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_PATH = 'video_documentation.db'
# Controls which text_extract to join when fetching slides:
# - 'latest' (default): use most recent text_extract by created_at,id
# - 'first': use earliest text_extract by created_at,id
TEXT_EXTRACT_SELECTION = os.getenv('TEXT_EXTRACT_SELECTION', 'latest')

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_path TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration REAL,
            fps REAL,
            processed BOOLEAN DEFAULT 0
        )
    ''')
    
    # Slides/frames extracted from video
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            frame_number INTEGER NOT NULL,
            timestamp REAL NOT NULL,
            image_path TEXT NOT NULL,
            order_index INTEGER,
            section_id INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos (id),
            FOREIGN KEY (section_id) REFERENCES sections (id)
        )
    ''')
    
    # Text extracts from audio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS text_extracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slide_id INTEGER NOT NULL,
            original_text TEXT,
            suggested_text TEXT,
            final_text TEXT,
            is_locked BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slide_id) REFERENCES slides (id)
        )
    ''')
    
    # Sections/chapters for organizing slides
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            create_new_page BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )
    ''')

    # Audio extraction failures for debugging and audit
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            slide_id INTEGER,
            start_frame INTEGER,
            end_frame INTEGER,
            attempts INTEGER,
            error_message TEXT,
            tool TEXT,
            stderr TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()

    # Backwards-compatible migration: add document fields if missing
    try:
        cursor.execute("PRAGMA table_info(videos)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'document_title' not in cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN document_title TEXT")
        if 'document_summary' not in cols:
            cursor.execute("ALTER TABLE videos ADD COLUMN document_summary TEXT")
        conn.commit()
    except Exception:
        logging.exception('Failed to run videos table migration (ignored)')
    
    # Migration: add create_new_page to sections if missing
    try:
        cursor.execute("PRAGMA table_info(sections)")
        secs = [r[1] for r in cursor.fetchall()]
        if 'create_new_page' not in secs:
            cursor.execute("ALTER TABLE sections ADD COLUMN create_new_page BOOLEAN DEFAULT 0")
            conn.commit()
    except Exception:
        logging.exception('Failed to run sections table migration (ignored)')
    
    # Migration: add order_index to slides if missing
    try:
        cursor.execute("PRAGMA table_info(slides)")
        slides_cols = [r[1] for r in cursor.fetchall()]
        if 'order_index' not in slides_cols:
            cursor.execute("ALTER TABLE slides ADD COLUMN order_index INTEGER")
            # Set initial order based on frame_number for existing slides
            cursor.execute("UPDATE slides SET order_index = frame_number WHERE order_index IS NULL")
            conn.commit()
    except Exception:
        logging.exception('Failed to run slides table migration (ignored)')

    # Migration: add structured fields to audio_failures (tool, stderr, details) if missing
    try:
        cursor.execute("PRAGMA table_info(audio_failures)")
        af_cols = [r[1] for r in cursor.fetchall()]
        if 'tool' not in af_cols:
            cursor.execute("ALTER TABLE audio_failures ADD COLUMN tool TEXT")
            conn.commit()
        if 'stderr' not in af_cols:
            cursor.execute("ALTER TABLE audio_failures ADD COLUMN stderr TEXT")
            conn.commit()
        if 'details' not in af_cols:
            cursor.execute("ALTER TABLE audio_failures ADD COLUMN details TEXT")
            conn.commit()
    except Exception:
        logging.exception('Failed to run audio_failures table migration (ignored)')

    conn.close()
    logging.info("Database initialized successfully")

def add_video(filename, original_path, duration=None, fps=None):
    """Add a new video to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO videos (filename, original_path, duration, fps)
        VALUES (?, ?, ?, ?)
    ''', (filename, original_path, duration, fps))
    video_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return video_id

def add_slide(video_id, frame_number, timestamp, image_path):
    """Add a slide/frame to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO slides (video_id, frame_number, timestamp, image_path, order_index)
        VALUES (?, ?, ?, ?, ?)
    ''', (video_id, frame_number, timestamp, image_path, frame_number))
    slide_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return slide_id

def add_slide_minimal(video_id, image_path=None):
    """Insert a minimal slide for testing. If image_path not provided, use a placeholder.
    Returns the new slide id."""
    # Ensure output folder exists and a stable placeholder image is available
    os.makedirs('output', exist_ok=True)
    placeholder_path = os.path.join('output', 'placeholder.jpg')
    if not image_path:
        # Create a tiny placeholder image if one doesn't exist
        if not os.path.exists(placeholder_path):
            try:
                from PIL import Image
                img = Image.new('RGB', (160, 120), color=(230, 230, 230))
                img.save(placeholder_path, format='JPEG')
            except Exception:
                # If PIL not available, fallback to an empty text file so file exists
                with open(placeholder_path, 'wb') as f:
                    f.write(b'')
        image_path = placeholder_path
    slide_id = add_slide(video_id, 0, 0.0, image_path)
    # Create an empty text_extract so update_text can operate without 404
    try:
        add_text_extract(slide_id, original_text='')
    except Exception:
        logging.exception('Failed to create placeholder text_extract for new slide (ignored)')
    return slide_id

def get_slide_by_id(slide_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM slides WHERE id = ? LIMIT 1', (slide_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_text_extract(slide_id, original_text, suggested_text=None):
    """Add text extract for a slide"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO text_extracts (slide_id, original_text, suggested_text)
        VALUES (?, ?, ?)
    ''', (slide_id, original_text, suggested_text))
    extract_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return extract_id

def update_text_extract(extract_id, final_text, is_locked=False):
    """Update the final text and lock status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE text_extracts 
        SET final_text = ?, is_locked = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (final_text, is_locked, extract_id))
    conn.commit()
    conn.close()

def get_video_slides(video_id):
    """Get all slides for a video"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Join to a single text_extract per slide. Choice is configurable via TEXT_EXTRACT_SELECTION.
    if TEXT_EXTRACT_SELECTION == 'first':
        order_clause = 'ORDER BY te.created_at ASC, te.id ASC'
    else:
        order_clause = 'ORDER BY te.created_at DESC, te.id DESC'

    cursor.execute(f'''
        SELECT s.*, t.original_text, t.suggested_text, t.final_text, t.is_locked
        FROM slides s
        LEFT JOIN text_extracts t ON s.id = t.slide_id
          AND t.id = (
              SELECT te.id FROM text_extracts te
              WHERE te.slide_id = s.id
              {order_clause} LIMIT 1
          )
        WHERE s.video_id = ?
        ORDER BY COALESCE(s.order_index, s.frame_number), s.frame_number
    ''', (video_id,))
    slides = cursor.fetchall()
    conn.close()
    return slides


def get_slide_by_frame(video_id, frame_number):
    """Return a slide row for a video matching the given frame number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM slides WHERE video_id = ? AND frame_number = ? LIMIT 1', (video_id, frame_number))
    row = cursor.fetchone()
    conn.close()
    return row


def get_previous_slide(video_id, order_index):
    """Return the slide immediately before the given order_index for a video, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM slides
        WHERE video_id = ? AND COALESCE(order_index, frame_number) < ?
        ORDER BY COALESCE(order_index, frame_number) DESC
        LIMIT 1
    ''', (video_id, order_index))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_next_slide(video_id, order_index):
    """Return the slide immediately after the given order_index for a video, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM slides
        WHERE video_id = ? AND COALESCE(order_index, frame_number) > ?
        ORDER BY COALESCE(order_index, frame_number) ASC
        LIMIT 1
    ''', (video_id, order_index))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_text_extract_by_slide(slide_id):
    """Return the text_extract row for a given slide_id, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM text_extracts WHERE slide_id = ? LIMIT 1', (slide_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def set_final_text_for_slide(slide_id, new_text, is_locked=False):
    """Set (or create) the final_text and lock status for the most recent extract of a slide."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Try to find an existing extract
    cursor.execute('SELECT id FROM text_extracts WHERE slide_id = ? ORDER BY created_at DESC, id DESC LIMIT 1', (slide_id,))
    r = cursor.fetchone()
    if r:
        extract_id = r['id']
        cursor.execute('UPDATE text_extracts SET final_text = ?, is_locked = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_text, int(bool(is_locked)), extract_id))
    else:
        cursor.execute('INSERT INTO text_extracts (slide_id, original_text, final_text, is_locked) VALUES (?, ?, ?, ?)', (slide_id, '', new_text, int(bool(is_locked))))
    conn.commit()
    conn.close()


def merge_from_slide_into_target(source_slide_id, target_slide_id, append=True):
    """
    Merge text from source slide into target slide.
    If append=True, source text is appended to target. If False, source text is prepended.
    After merge, source slide and its extracts are deleted.
    Returns dict with target_slide and deleted source info.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch source and target slides
        cursor.execute('SELECT * FROM slides WHERE id = ? LIMIT 1', (source_slide_id,))
        src = cursor.fetchone()
        cursor.execute('SELECT * FROM slides WHERE id = ? LIMIT 1', (target_slide_id,))
        tgt = cursor.fetchone()
        if not src or not tgt:
            conn.close()
            return None

        # Get latest extracts
        cursor.execute('SELECT * FROM text_extracts WHERE slide_id = ? ORDER BY created_at DESC, id DESC LIMIT 1', (source_slide_id,))
        src_txt = cursor.fetchone()
        cursor.execute('SELECT * FROM text_extracts WHERE slide_id = ? ORDER BY created_at DESC, id DESC LIMIT 1', (target_slide_id,))
        tgt_txt = cursor.fetchone()

        src_text = (src_txt['final_text'] if src_txt and src_txt['final_text'] else (src_txt['suggested_text'] if src_txt else '')) if src_txt else ''
        tgt_text = (tgt_txt['final_text'] if tgt_txt and tgt_txt['final_text'] else (tgt_txt['suggested_text'] if tgt_txt else '')) if tgt_txt else ''

        if append:
            merged = (tgt_text or '') + (('\n' + src_text) if src_text else '')
        else:
            merged = (src_text or '') + (('\n' + tgt_text) if tgt_text else '')

        # Update or create target extract
        cursor.execute('SELECT id FROM text_extracts WHERE slide_id = ? ORDER BY created_at DESC, id DESC LIMIT 1', (target_slide_id,))
        r = cursor.fetchone()
        if r:
            cursor.execute('UPDATE text_extracts SET final_text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (merged, r['id']))
        else:
            cursor.execute('INSERT INTO text_extracts (slide_id, original_text, final_text) VALUES (?, ?, ?)', (target_slide_id, tgt_text, merged))

        # Capture source image path (best-effort) then delete source slide and its extracts
        src_image_path = src['image_path'] if src and 'image_path' in src.keys() else None
        cursor.execute('DELETE FROM text_extracts WHERE slide_id = ?', (source_slide_id,))
        cursor.execute('DELETE FROM slides WHERE id = ?', (source_slide_id,))

        conn.commit()
        return {
            'target_slide_id': target_slide_id,
            'merged_text': merged,
            'deleted_source_id': source_slide_id,
            'deleted_source_image': src_image_path,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_text_extract_original_suggested(extract_id, original_text, suggested_text=None):
    """Update the original_text and suggested_text fields for an extract."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE text_extracts
        SET original_text = ?, suggested_text = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (original_text, suggested_text, extract_id))
    conn.commit()
    conn.close()

def create_section(video_id, title, order_index, create_new_page=False):
    """Create a new section/chapter. create_new_page indicates whether the PDF should start the section on a new page."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sections (video_id, title, order_index, create_new_page)
        VALUES (?, ?, ?, ?)
    ''', (video_id, title, order_index, int(bool(create_new_page))))
    section_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return section_id

def delete_section(section_id):
    """Delete a section and unassign all slides from it."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First, unassign all slides from this section
        cursor.execute('UPDATE slides SET section_id = NULL WHERE section_id = ?', (section_id,))
        
        # Then delete the section
        cursor.execute('DELETE FROM sections WHERE id = ?', (section_id,))
        
        conn.commit()
        return cursor.rowcount > 0  # Return True if section was deleted
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def assign_slide_to_section(slide_id, section_id):
    """Assign a slide to a section"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE slides SET section_id = ? WHERE id = ?
    ''', (section_id, slide_id))
    conn.commit()
    conn.close()


def delete_slide(slide_id):
    """Delete a slide and its associated text_extracts and optionally image file path reference."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch slide row
        cursor.execute('SELECT * FROM slides WHERE id = ? LIMIT 1', (slide_id,))
        slide_row = cursor.fetchone()
        slide = dict(slide_row) if slide_row else None

        # Fetch any associated text extracts
        cursor.execute('SELECT * FROM text_extracts WHERE slide_id = ? ORDER BY created_at ASC', (slide_id,))
        extracts = [dict(r) for r in cursor.fetchall()]

        # Delete the text extracts and the slide; capture affected row counts
        cursor.execute('DELETE FROM text_extracts WHERE slide_id = ?', (slide_id,))
        extracts_deleted = cursor.rowcount
        cursor.execute('DELETE FROM slides WHERE id = ?', (slide_id,))
        slides_deleted = cursor.rowcount
        conn.commit()
    finally:
        conn.close()

    # Return the slide and extracts so callers can offer an undo/backup
    image_path = slide.get('image_path') if slide else None
    return {'slide': slide, 'extracts': extracts, 'image_path': image_path, 'counts': {'slides_deleted': slides_deleted, 'extracts_deleted': extracts_deleted}}

def get_sections_by_video(video_id):
    """Get all sections for a video"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM sections WHERE video_id = ? ORDER BY order_index
    ''', (video_id,))
    sections = cursor.fetchall()
    conn.close()
    return sections

def get_slides_by_section(section_id):
    """Get all slides in a section"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Join to only the most recent text_extract per slide to avoid duplicate rows
    cursor.execute('''
        SELECT s.*, t.original_text, t.suggested_text, t.final_text, t.is_locked
        FROM slides s
        LEFT JOIN text_extracts t ON s.id = t.slide_id
          AND t.id = (
              SELECT te.id FROM text_extracts te
              WHERE te.slide_id = s.id
              ORDER BY te.created_at DESC, te.id DESC LIMIT 1
          )
        WHERE s.section_id = ?
        ORDER BY COALESCE(s.order_index, s.frame_number), s.frame_number
    ''', (section_id,))
    slides = cursor.fetchall()
    conn.close()
    return slides

def get_processed_videos():
    """Return all processed videos along with slide counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.id, v.filename, v.upload_date, v.processed,
               COUNT(s.id) AS slide_count
        FROM videos v
        LEFT JOIN slides s ON s.video_id = v.id
        WHERE v.processed = 1
        GROUP BY v.id
        ORDER BY v.upload_date DESC, v.id DESC
    ''')
    videos = cursor.fetchall()
    conn.close()
    return videos


def get_all_videos():
    """Return all videos along with slide counts and document metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT v.id, v.filename, v.upload_date, v.processed,
               COUNT(s.id) AS slide_count, v.document_title, v.document_summary
        FROM videos v
        LEFT JOIN slides s ON s.video_id = v.id
        GROUP BY v.id
        ORDER BY v.upload_date DESC, v.id DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_video(video_id):
    """Delete a video and all related slides, text_extracts, sections, and audio_failures.
    This function removes DB rows and returns metadata about deleted items so callers
    can perform best-effort filesystem cleanup (images, wavs).
    Returns dict with keys: video (row or None), slides (list of slide rows), image_paths (list)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get video row
        cursor.execute('SELECT * FROM videos WHERE id = ? LIMIT 1', (video_id,))
        video_row = cursor.fetchone()
        video = dict(video_row) if video_row else None

        # Get all slides for the video
        cursor.execute('SELECT * FROM slides WHERE video_id = ?', (video_id,))
        slides_rows = cursor.fetchall()
        slides = [dict(r) for r in slides_rows]

        # Capture image paths for cleanup
        image_paths = [s.get('image_path') for s in slides if s.get('image_path')]

        # Delete text extracts for these slides
        slide_ids = [s['id'] for s in slides]
        if slide_ids:
            cursor.execute('DELETE FROM text_extracts WHERE slide_id IN ({})'.format(','.join('?' for _ in slide_ids)), slide_ids)
            extracts_deleted = cursor.rowcount
        else:
            extracts_deleted = 0

        # Delete slides
        cursor.execute('DELETE FROM slides WHERE video_id = ?', (video_id,))
        slides_deleted = cursor.rowcount

        # Delete sections belonging to this video
        cursor.execute('DELETE FROM sections WHERE video_id = ?', (video_id,))
        sections_deleted = cursor.rowcount

        # Delete audio_failures for this video
        cursor.execute('DELETE FROM audio_failures WHERE video_id = ?', (video_id,))
        af_deleted = cursor.rowcount

        # Finally delete the video record itself
        cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
        videos_deleted = cursor.rowcount

        conn.commit()

        return {
            'video': video,
            'slides': slides,
            'image_paths': image_paths,
            'counts': {
                'videos_deleted': videos_deleted,
                'slides_deleted': slides_deleted,
                'extracts_deleted': extracts_deleted,
                'sections_deleted': sections_deleted,
                'audio_failures_deleted': af_deleted,
            }
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_video_document(video_id, title: str | None, summary: str | None):
    """Update document title and summary for a video."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE videos
        SET document_title = ?, document_summary = ?
        WHERE id = ?
    ''', (title, summary, video_id))
    conn.commit()
    conn.close()

def get_video_by_id(video_id):
    """Fetch a single video record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def add_audio_failure(video_id, slide_id, start_frame, end_frame, attempts, error_message, tool=None, stderr=None, details=None):
    """Record an audio extraction or transcription failure for later inspection.

    New optional structured fields:
      - tool: which tool failed (e.g. 'ffmpeg', 'moviepy', 'whisper')
      - stderr: raw STDERR or error message
      - details: any additional debugging details
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audio_failures (video_id, slide_id, start_frame, end_frame, attempts, error_message, tool, stderr, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (video_id, slide_id, start_frame, end_frame, attempts, error_message, tool, stderr, details))
    failure_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return failure_id


def get_audio_failures(limit: int = 100, video_id: int = None):
    """Return recent audio extraction failures, optionally filtered by video_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if video_id is not None:
        cursor.execute('''
            SELECT af.*, v.filename
            FROM audio_failures af
            LEFT JOIN videos v ON v.id = af.video_id
            WHERE af.video_id = ?
            ORDER BY af.created_at DESC
            LIMIT ?
        ''', (video_id, limit))
    else:
        cursor.execute('''
            SELECT af.*, v.filename
            FROM audio_failures af
            LEFT JOIN videos v ON v.id = af.video_id
            ORDER BY af.created_at DESC
            LIMIT ?
        ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def restore_slide(slide_row: dict, extracts: list[dict]):
    """Restore a slide row and its extracts. slide_row is a dict containing slide fields."""
    if not slide_row:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Insert slide (preserve id if possible via explicit id insert)
        # SQLite supports explicit id insertion if it doesn't conflict.
        cols = [k for k in slide_row.keys() if k != 'id']
        placeholders = ','.join('?' for _ in cols)
        values = [slide_row[c] for c in cols]
        # Try to preserve id; if fails, insert without id
        try:
            cursor.execute('INSERT INTO slides (id, ' + ','.join(cols) + ') VALUES (' + ','.join('?' for _ in (['id']+cols)) + ')', [slide_row['id']] + values)
        except Exception:
            cursor.execute('INSERT INTO slides (' + ','.join(cols) + ') VALUES (' + placeholders + ')', values)
            slide_row['id'] = cursor.lastrowid

        # Restore extracts
        for ex in extracts:
            cols_ex = [k for k in ex.keys() if k != 'id']
            placeholders_ex = ','.join('?' for _ in cols_ex)
            values_ex = [ex[c] for c in cols_ex]
            try:
                cursor.execute('INSERT INTO text_extracts (id, ' + ','.join(cols_ex) + ') VALUES (' + ','.join('?' for _ in (['id']+cols_ex)) + ')', [ex['id']] + values_ex)
            except Exception:
                cursor.execute('INSERT INTO text_extracts (' + ','.join(cols_ex) + ') VALUES (' + placeholders_ex + ')', values_ex)

        conn.commit()
    finally:
        conn.close()
    return slide_row

def get_latest_video_with_slides():
    """Return the most recently processed video ID that has slide data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT v.id
        FROM videos v
        WHERE EXISTS (
            SELECT 1 FROM slides s WHERE s.video_id = v.id
        )
        ORDER BY v.upload_date DESC, v.id DESC
        LIMIT 1
    ''')
    row = cursor.fetchone()

    if not row:
        cursor.execute('''
            SELECT id FROM videos
            ORDER BY upload_date DESC, id DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()

    conn.close()
    return row['id'] if row else None

def mark_video_processed(video_id):
    """Mark a video as processed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE videos SET processed = 1 WHERE id = ?
    ''', (video_id,))
    conn.commit()
    conn.close()


def update_video_document(video_id, title, summary):
    """Update document title and summary for a video."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE videos
        SET document_title = ?, document_summary = ?
        WHERE id = ?
    ''', (title, summary, video_id))
    conn.commit()
    conn.close()


def reorder_slide(slide_id, direction):
    """Move a slide up or down in the ordering sequence"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current slide info
    cursor.execute('SELECT video_id, order_index FROM slides WHERE id = ?', (slide_id,))
    slide = cursor.fetchone()
    if not slide:
        conn.close()
        return False
    
    video_id, current_order = slide
    
    # Get all slides for this video ordered by current order
    cursor.execute('''
        SELECT id, order_index FROM slides 
        WHERE video_id = ? 
        ORDER BY COALESCE(order_index, frame_number), frame_number
    ''', (video_id,))
    slides = cursor.fetchall()
    
    # Find current position
    current_pos = None
    for i, (sid, order) in enumerate(slides):
        if sid == slide_id:
            current_pos = i
            break
    
    if current_pos is None:
        conn.close()
        return False
    
    # Calculate new position
    if direction == 'up' and current_pos > 0:
        new_pos = current_pos - 1
    elif direction == 'down' and current_pos < len(slides) - 1:
        new_pos = current_pos + 1
    else:
        conn.close()
        return False  # Can't move further
    
    # Swap order_index with the target slide
    target_slide_id = slides[new_pos][0]
    
    # Get current order_index values
    cursor.execute('SELECT order_index FROM slides WHERE id = ?', (slide_id,))
    current_order = cursor.fetchone()[0]
    cursor.execute('SELECT order_index FROM slides WHERE id = ?', (target_slide_id,))
    target_order = cursor.fetchone()[0]
    
    # Swap the order_index values
    cursor.execute('UPDATE slides SET order_index = ? WHERE id = ?', (target_order, slide_id))
    cursor.execute('UPDATE slides SET order_index = ? WHERE id = ?', (current_order, target_slide_id))
    
    conn.commit()
    conn.close()
    return True


def set_slide_order(slide_id, order_index):
    """Set the order index for a specific slide"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE slides SET order_index = ? WHERE id = ?', (order_index, slide_id))
    conn.commit()
    conn.close()
    return True


def get_all_slides_for_export():
    """Get all slides with related data for CSV export"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query slides with related data using JOINs
    cursor.execute('''
        SELECT 
            s.id,
            s.video_id,
            s.frame_number,
            s.timestamp,
            s.image_path,
            s.order_index,
            s.section_id,
            v.filename as video_filename,
            sec.title as section_title,
            sec.create_new_page,
            te.final_text,
            te.suggested_text,
            te.original_text,
            te.is_locked
        FROM slides s
        JOIN videos v ON s.video_id = v.id
        LEFT JOIN sections sec ON s.section_id = sec.id
        LEFT JOIN text_extracts te ON s.id = te.slide_id
        ORDER BY s.video_id, s.order_index, s.frame_number
    ''')
    
    slides = cursor.fetchall()
    conn.close()
    return slides


def purge_audio_failures_older_than(days: int) -> int:
    """Delete audio_failures older than `days` days and return number deleted.

    Uses timezone-aware UTC timestamps for comparison to avoid ambiguity and
    avoid DeprecationWarnings from datetime.utcnow().
    """
    from datetime import datetime, timedelta, timezone
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
    # SQLite CURRENT_TIMESTAMP is in 'YYYY-MM-DD HH:MM:SS' (UTC); format cutoff accordingly
    cutoff = cutoff_dt.strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('DELETE FROM audio_failures WHERE created_at < ?', (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
