"""Deprecated root module.

The application moved into the `vid2doc` package as `vid2doc.app`. Import
from that package instead. This explicit ImportError avoids silent shims and
encourages consumers to use the packaged location.
"""

raise ImportError("module 'app' moved: import from 'vid2doc.app' instead")


@app.route('/export/slides_csv')
def export_slides_csv():
    """Export all slides with their details to CSV for backup."""
    try:
        # Get all slides with related data
        slides = get_all_slides_for_export()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Slide ID',
            'Video Filename', 
            'Frame Number',
            'Timestamp (seconds)',
            'Order Index',
            'Section Title',
            'Create New Page',
            'Final Text',
            'Is Locked',
            'Image Path'
        ])
        
        # Write data rows
        for slide in slides:
            # Use final_text if available, otherwise suggested_text, otherwise original_text
            text_content = slide['final_text']
            if not text_content:
                text_content = slide['suggested_text']
            if not text_content:
                text_content = slide['original_text']
            text_content = text_content or ''
            
            writer.writerow([
                slide['id'],
                slide['video_filename'],
                slide['frame_number'],
                slide['timestamp'],
                slide['order_index'] or '',
                slide['section_title'] or '',
                'Yes' if slide['create_new_page'] else 'No',
                text_content,
                'Yes' if slide['is_locked'] else 'No',
                slide['image_path']
            ])
        
        # Create response
        output.seek(0)
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=slides_backup.csv'
            }
        )
        return response
        
    except Exception as e:
        logging.exception('Failed to export slides to CSV')
        flash(f'Error exporting slides: {str(e)}', 'error')
        return redirect(url_for('system_settings'))


def _list_wav_files():
    files = []
    for fn in os.listdir('wav'):
        if fn.lower().endswith('.wav'):
            files.append(os.path.join('wav', fn))
    return files


@app.route('/api/list_orphan_wavs')
def api_list_orphan_wavs():
    """Return list of wav files that are not referenced in the DB."""
    try:
        existing = set(_list_wav_files())
        # Find wavs referenced in DB by filename
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT original_text FROM text_extracts')
        texts = [r['original_text'] for r in cursor.fetchall()]
        conn.close()

        # Naive heuristic: if filename appears in any stored text or in output paths, consider it referenced.
        referenced = set()
        for t in texts:
            if not t:
                continue
            for f in existing:
                if os.path.basename(f) in t:
                    referenced.add(f)

        orphans = sorted(list(existing - referenced))
        return jsonify({'success': True, 'files': orphans})
    except Exception as e:
        logging.exception('Failed to list orphan wavs')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/clear_orphan_wavs', methods=['POST'])
def api_clear_orphan_wavs():
    """Delete orphan wav files determined by the same heuristic as listing."""
    try:
        listed = api_list_orphan_wavs().get_json()
        if not listed.get('success'):
            return jsonify({'success': False, 'message': 'Failed to compute orphan list'}), 500
        files = listed.get('files', [])
        deleted = []
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    deleted.append(f)
            except Exception:
                logging.exception('Failed to delete wav file: %s', f)
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        logging.exception('Failed to clear orphan wavs')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/reinit_db', methods=['POST'])
def api_reinit_db():
    """Re-run database initialization/migrations."""
    try:
        init_db()
        return jsonify({'success': True, 'message': 'DB initialization complete'})
    except Exception as e:
        logging.exception('Failed to reinit DB')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/reset_db', methods=['POST'])
def api_reset_db():
    """Dangerous: resets database by dropping tables and reinitializing schema.
    Requires JSON { confirm: true }.
    """
    data = request.get_json() or {}
    if not data.get('confirm'):
        return jsonify({'success': False, 'message': 'Confirmation required'}), 400
    try:
        # Remove database file and re-run init
        db_path = os.path.abspath('video_documentation.db')
        if os.path.exists(db_path):
            os.remove(db_path)
        init_db()
        return jsonify({'success': True, 'message': 'Database reset and reinitialized'})
    except Exception as e:
        logging.exception('Failed to reset DB')
        return jsonify({'success': False, 'message': str(e)}), 500



def _resolve_nav_edit_url(preferred_video_id=None):
    """Determine the navigation URL for editing slides."""
    if preferred_video_id:
        return url_for('edit_video', video_id=preferred_video_id)

    latest_video_id = get_latest_video_with_slides()
    if latest_video_id:
        return url_for('edit_video', video_id=latest_video_id)

    return url_for('edit_latest')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', nav_edit_url=_resolve_nav_edit_url())

@app.route('/upload', methods=['GET', 'POST'])
def upload_video():
    """Upload and process video"""
    # Legacy route maintained for backwards compatibility.
    if request.method == 'POST':
        flash('Please use the new dashboard interface to upload videos.', 'error')
    return render_template('index.html', nav_edit_url=_resolve_nav_edit_url())


@app.route('/document-editing')
def document_editing():
    """Document Editing landing page with video selector."""
    videos = get_all_videos()
    return render_template('edit_video.html', video_id=None, slides=[], sections=[], videos=videos, nav_edit_url=_resolve_nav_edit_url())


@app.route('/edit/latest')
def edit_latest():
    """Redirect to the most recent video with slide data."""
    latest_video_id = get_latest_video_with_slides()
    if latest_video_id:
        return redirect(url_for('edit_video', video_id=latest_video_id))

    flash('No processed videos are available yet. Upload a video to get started.', 'error')
    return redirect(url_for('index'))

@app.route('/video/<int:video_id>')
def edit_video(video_id):
    """Edit video slides and text"""
    slides = get_video_slides(video_id)
    sections = get_sections_by_video(video_id)
    print(f"DEBUG: Found {len(sections)} sections for video {video_id}")
    for s in sections:
        create_new_page = s['create_new_page'] if 'create_new_page' in s else 'MISSING'
        print(f"DEBUG: Section {s['id']}: {s['title']} - create_new_page: {create_new_page}")
    videos = get_all_videos()
    video = get_video_by_id(video_id)
    document_title = video['document_title'] if video else ''
    document_summary = video['document_summary'] if video else ''
    return render_template(
        'edit_video.html',
        video_id=video_id,
        slides=slides,
        sections=sections,
        videos=videos,
        document_title=document_title,
        document_summary=document_summary,
        nav_edit_url=_resolve_nav_edit_url(video_id),
    )





@app.route('/review', defaults={'video_id': None})
@app.route('/review/<int:video_id>')
def review_video(video_id):
    """Review captured slides with editable text"""
    processed_videos = get_processed_videos()

    selected_video_id = video_id
    slides = []
    selected_video = None

    if processed_videos:
        if selected_video_id is None:
            prioritized = next((v for v in processed_videos if v['slide_count'] > 0), processed_videos[0])
            selected_video_id = prioritized['id']

        if selected_video_id is not None:
            selected_video = get_video_by_id(selected_video_id)
            if not selected_video:
                abort(404)
            slides = get_video_slides(selected_video_id) or []
            if not slides:
                flash('No slides found for this video yet. Process the video first.', 'error')
    elif selected_video_id is not None:
        # Requested video doesn't exist in processed list
        selected_video = get_video_by_id(selected_video_id)
        if not selected_video:
            abort(404)
        slides = get_video_slides(selected_video_id) or []
        if not slides:
            flash('No slides found for this video yet. Process the video first.', 'error')

    return render_template(
        'review_video.html',
        video_id=selected_video_id,
        selected_video=selected_video,
        processed_videos=processed_videos,
        slides=slides,
        nav_edit_url=_resolve_nav_edit_url(selected_video_id),
    )

@app.route('/api/update_text/<int:slide_id>', methods=['POST'])
def update_text(slide_id):
    """API endpoint to update text for a slide"""
    data = request.get_json()
    final_text = data.get('final_text', '')
    is_locked = data.get('is_locked', False)
    
    try:
        # Find the text extract ID for this slide
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        # Pick the most recent text_extract for this slide (match get_video_slides ordering)
        cursor.execute('SELECT id FROM text_extracts WHERE slide_id = ? ORDER BY created_at DESC, id DESC LIMIT 1', (slide_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            extract_id = result['id']
            update_text_extract(extract_id, final_text, is_locked)
            # return the updated extract for confirmation
            from database import get_db_connection
            conn2 = get_db_connection()
            cur2 = conn2.cursor()
            cur2.execute('SELECT id, slide_id, original_text, suggested_text, final_text, is_locked, created_at, updated_at FROM text_extracts WHERE id = ?', (extract_id,))
            row = cur2.fetchone()
            conn2.close()
            return jsonify({'success': True, 'message': 'Text updated successfully', 'extract': dict(row) if row else None})
        else:
            # Create a placeholder text_extract for this slide so callers can save text
            try:
                new_id = add_text_extract(slide_id, original_text='')
                update_text_extract(new_id, final_text, is_locked)
                conn2 = get_db_connection()
                cur2 = conn2.cursor()
                cur2.execute('SELECT id, slide_id, original_text, suggested_text, final_text, is_locked, created_at, updated_at FROM text_extracts WHERE id = ?', (new_id,))
                row = cur2.fetchone()
                conn2.close()
                return jsonify({'success': True, 'message': 'Text created and updated', 'extract': dict(row) if row else None})
            except Exception as e:
                logging.exception('Failed to create text extract')
                return jsonify({'success': False, 'message': 'Text extract not found and creation failed'}), 500
    
    except Exception as e:
        logging.error(f"Error updating text: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/create_section/<int:video_id>', methods=['POST'])
def create_section_api(video_id):
    """API endpoint to create a new section"""
    data = request.get_json()
    title = data.get('title', '')
    create_new_page = bool(data.get('create_new_page', False))
    if not title:
        return jsonify({'success': False, 'message': 'Section title required'}), 400
    
    try:
        # Get next order index
        sections = get_sections_by_video(video_id)
        order_index = len(sections)

        section_id = create_section(video_id, title, order_index, create_new_page=create_new_page)
        return jsonify({'success': True, 'section_id': section_id, 'title': title, 'order_index': order_index, 'create_new_page': create_new_page})
    except Exception as e:
        logging.error(f"Error creating section: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/delete_section/<int:section_id>', methods=['POST'])
def delete_section_api(section_id):
    """API endpoint to delete a section"""
    try:
        from database import delete_section
        success = delete_section(section_id)
        if success:
            return jsonify({'success': True, 'message': 'Section deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Section not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting section: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/assign_to_section/<int:slide_id>', methods=['POST'])
def assign_to_section(slide_id):
    """API endpoint to assign a slide to a section"""
    data = request.get_json()
    section_id = data.get('section_id')
    
    try:
        assign_slide_to_section(slide_id, section_id)
        return jsonify({'success': True, 'message': 'Slide assigned to section'})
    
    except Exception as e:
        logging.error(f"Error assigning slide: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete_slide/<int:slide_id>', methods=['POST'])
def api_delete_slide(slide_id):
    """API endpoint to delete a slide and its text extracts."""
    try:
        from database import delete_slide
        res = delete_slide(slide_id)
        image_path = res.get('image_path') if isinstance(res, dict) else None
        counts = res.get('counts', {}) if isinstance(res, dict) else {}
        if counts.get('slides_deleted', 0) == 0:
            return jsonify({'success': False, 'message': 'Slide not found or already deleted'}), 404

        # Best-effort: remove image file from output folder
        try:
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            logging.exception('Failed to remove slide image file (ignored)')

        return jsonify({'success': True, 'deleted': res})
    except Exception as e:
        logging.exception(f"Failed to delete slide {slide_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/add_slide/<int:video_id>', methods=['POST'])
def api_add_slide(video_id):
    """Create a minimal slide record for testing/debugging.
    This inserts a slide record with frame_number=0 and timestamp=0 and returns the created slide.
    """
    try:
        from database import add_slide_minimal, get_slide_by_id
        new_id = add_slide_minimal(video_id)
        slide = get_slide_by_id(new_id)
        return jsonify({'success': True, 'slide': slide})
    except Exception as e:
        logging.exception('Failed to add slide')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/undelete_slide', methods=['POST'])
def api_undelete_slide():
    """Restore a previously deleted slide using payload { slide: {...}, extracts: [...] }"""
    data = request.get_json() or {}
    slide = data.get('slide')
    extracts = data.get('extracts') or []
    if not slide:
        return jsonify({'success': False, 'message': 'No slide data provided'}), 400
    try:
        from database import restore_slide
        restored = restore_slide(slide, extracts)
        return jsonify({'success': True, 'restored': restored})
    except Exception as e:
        logging.exception('Failed to restore slide')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/reorder_slide/<int:slide_id>', methods=['POST'])
def api_reorder_slide(slide_id):
    """Reorder a slide by moving it up or down in the sequence"""
    data = request.get_json() or {}
    direction = data.get('direction')  # 'up' or 'down'
    
    if direction not in ['up', 'down']:
        return jsonify({'success': False, 'message': 'Invalid direction. Must be "up" or "down"'}), 400
    
    try:
        from database import reorder_slide
        success = reorder_slide(slide_id, direction)
        return jsonify({'success': success})
    except Exception as e:
        logging.exception('Failed to reorder slide')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/merge_above/<int:slide_id>', methods=['POST'])
def api_merge_above(slide_id):
    """Merge the slide above into the given slide (prepend source to target)"""
    try:
        # Find current slide and its order_index / video_id
        from database import get_slide_by_id, merge_from_slide_into_target
        cur = get_slide_by_id(slide_id)
        if not cur:
            return jsonify({'success': False, 'message': 'Slide not found'}), 404

        video_id = cur['video_id']
        order_index = cur.get('order_index') or cur.get('frame_number')
        from database import get_previous_slide
        prev = get_previous_slide(video_id, order_index)
        if not prev:
            return jsonify({'success': False, 'message': 'No previous slide to merge'}), 400

        res = merge_from_slide_into_target(prev['id'], slide_id, append=False)
        if not res:
            return jsonify({'success': False, 'message': 'Merge failed'}), 500
        # Best-effort cleanup of deleted slide image
        try:
            img = res.get('deleted_source_image')
            if img and os.path.exists(img):
                os.remove(img)
        except Exception:
            logging.exception('Failed to remove merged source image (ignored)')
        return jsonify({'success': True, 'merged': res})
    except Exception as e:
        logging.exception('Failed to merge above')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/merge_below/<int:slide_id>', methods=['POST'])
def api_merge_below(slide_id):
    """Merge the slide below into the given slide (append source to target)"""
    try:
        from database import get_slide_by_id, merge_from_slide_into_target
        cur = get_slide_by_id(slide_id)
        if not cur:
            return jsonify({'success': False, 'message': 'Slide not found'}), 404

        video_id = cur['video_id']
        order_index = cur.get('order_index') or cur.get('frame_number')
        from database import get_next_slide
        nxt = get_next_slide(video_id, order_index)
        if not nxt:
            return jsonify({'success': False, 'message': 'No next slide to merge'}), 400

        res = merge_from_slide_into_target(nxt['id'], slide_id, append=True)
        if not res:
            return jsonify({'success': False, 'message': 'Merge failed'}), 500
        try:
            img = res.get('deleted_source_image')
            if img and os.path.exists(img):
                os.remove(img)
        except Exception:
            logging.exception('Failed to remove merged source image (ignored)')
        return jsonify({'success': True, 'merged': res})
    except Exception as e:
        logging.exception('Failed to merge below')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/set_slide_order/<int:slide_id>', methods=['POST'])
def api_set_slide_order(slide_id):
    """Set the order index for a specific slide"""
    data = request.get_json() or {}
    order_index = data.get('order_index')
    
    if order_index is None or not isinstance(order_index, int):
        return jsonify({'success': False, 'message': 'Valid order_index (integer) required'}), 400
    
    try:
        from database import set_slide_order
        success = set_slide_order(slide_id, order_index)
        return jsonify({'success': success})
    except Exception as e:
        logging.exception('Failed to set slide order')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/export/<int:video_id>')
def export_pdf(video_id):
    """Export video to PDF"""
    try:
        # Get video record to extract document title and summary
        video = get_video_by_id(video_id)
        document_title = video['document_title'] if video and video['document_title'] else f"Video {video_id} Documentation"
        document_summary = video['document_summary'] if video and video['document_summary'] else "No summary provided. Use the 'Document Title' and 'Document Summary' fields in the video editor to add custom title and summary pages to your PDF."
        
        # Always use document title with spaces replaced by underscores for filename
        filename = document_title.replace(' ', '_') + '.pdf'

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f'video_{video_id}.pdf')
        generate_pdf_from_video_id(video_id, output_path, document_title, document_summary)
        
        # Ensure the file exists before sending
        if not os.path.exists(output_path):
            logging.error(f"PDF file was not created: {output_path}")
            return "Error: PDF could not be generated", 500
        
        # Read the file and return as Response with proper headers
        with open(output_path, 'rb') as f:
            pdf_data = f.read()
        
        response = Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={filename}',
                'Content-Length': len(pdf_data)
            }
        )
        return response
    
    except Exception as e:
        logging.error(f"Error exporting PDF: {e}")
        return f"Error generating PDF: {str(e)}", 500
@app.route('/api/videos')
def api_videos():
    vids = get_all_videos()
    out = []
    for v in vids:
        out.append({
            'id': v['id'],
            'filename': v['filename'],
            'slide_count': v['slide_count'] if 'slide_count' in v.keys() else 0,
            'document_title': v['document_title'] if 'document_title' in v.keys() else None,
            'document_summary': v['document_summary'] if 'document_summary' in v.keys() else None,
        })
    return jsonify({'success': True, 'videos': out})


@app.route('/api/video/<int:video_id>/document')
def api_get_document(video_id):
    video = get_video_by_id(video_id)
    if not video:
        return jsonify({'success': False, 'message': 'Video not found'}), 404
    return jsonify({
        'success': True,
        'document_title': video['document_title'] if 'document_title' in video.keys() else None,
        'document_summary': video['document_summary'] if 'document_summary' in video.keys() else None,
    })


@app.route('/api/update_document/<int:video_id>', methods=['POST'])
def api_update_document(video_id):
    data = request.get_json() or {}
    title = data.get('title', '')
    summary = data.get('summary', '')
    try:
        update_video_document(video_id, title, summary)
        return jsonify({'success': True})
    except Exception as e:
        logging.exception('Failed to update document')
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete_video/<int:video_id>', methods=['POST'])
def api_delete_video(video_id):
    """Delete a video/document and all associated slides, text extracts, sections, wav and image files.
    Returns a summary of what was deleted. Files are removed best-effort; DB deletion is transactional.
    """
    try:
        from database import delete_video, get_db_connection
        res = delete_video(video_id)
        if not res or res.get('counts', {}).get('videos_deleted', 0) == 0:
            return jsonify({'success': False, 'message': 'Video not found or already deleted'}), 404

        deleted_files = []
        failed_files = []

        # Remove slide images
        for img in res.get('image_paths', []) or []:
            try:
                if img and os.path.exists(img):
                    os.remove(img)
                    deleted_files.append(img)
            except Exception:
                logging.exception('Failed to remove slide image (ignored): %s', img)
                failed_files.append(img)

        # Attempt to remove wavs associated with the video using known patterns
        try:
            # Determine base filename from video record if available
            base_name = None
            if res.get('video') and res['video'].get('filename'):
                base_name = os.path.splitext(os.path.basename(res['video']['filename']))[0]

            wav_dir = os.path.join(os.getcwd(), 'wav')
            candidates = []
            # If WAV_FILENAME_PATTERN set, attempt to expand it across possible slide ranges
            pattern = app.config.get('WAV_FILENAME_PATTERN')
            if pattern and base_name:
                # We don't know prev/frame pairs reliably here, so glob for anything starting with base_name
                search = os.path.join(wav_dir, '**', f"{base_name}*.wav")
                import glob
                candidates.extend(glob.glob(search, recursive=True))

            # Also include simple pattern base-*.wav
            if base_name:
                import glob
                candidates.extend(glob.glob(os.path.join(wav_dir, f"**/{base_name}-*.wav"), recursive=True))

            # Deduplicate
            candidates = list(dict.fromkeys(candidates))

            for c in candidates:
                try:
                    if os.path.exists(c):
                        os.remove(c)
                        deleted_files.append(c)
                except Exception:
                    logging.exception('Failed to remove wav file (ignored): %s', c)
                    failed_files.append(c)
        except Exception:
            logging.exception('Failed to cleanup wav files (ignored)')

        return jsonify({'success': True, 'deleted': res.get('counts', {}), 'deleted_files': deleted_files, 'failed_files': failed_files})
    except Exception as e:
        logging.exception('Failed to delete video %s', video_id)
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/video/<int:video_id>/slides')
def api_video_slides(video_id):
    slides = get_video_slides(video_id) or []
    out = []
    for s in slides:
        out.append({
            'id': s['id'],
            'frame_number': s['frame_number'],
            'timestamp': s['timestamp'],
            'image_url': url_for('output_file', filename=os.path.basename(s['image_path'])),
            'original_text': s['original_text'],
            'final_text': s['final_text'],
            'is_locked': bool(s['is_locked']),
            'section_id': s['section_id'],
        })
    return jsonify({'success': True, 'slides': out})


def _append_log(job, message):
    job['logs'].append({'message': message, 'timestamp': time.time()})
    if len(job['logs']) > MAX_LOG_ENTRIES:
        job['logs'].pop(0)


# Progress throttling: minimum interval (seconds) between percent/log updates per job
PROGRESS_THROTTLE_SECONDS = 0.5
# Minimum percent delta required to push an update even if throttle window hasn't passed
PROGRESS_MIN_DELTA = 1.0


def _add_extract(job, extract):
    if not extract:
        return
    job['extracts'].append(extract)
    if len(job['extracts']) > MAX_EXTRACTS:
        job['extracts'].pop(0)


def _normalize_properties(properties):
    normalized = {}
    for key, value in properties.items():
        if isinstance(value, bool):
            normalized[key] = value
        elif isinstance(value, int):
            normalized[key] = int(value)
        elif isinstance(value, float):
            normalized[key] = float(value)
        else:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                normalized[key] = value
    return normalized


def _run_processing_job(job_id):
    with jobs_lock:
        job = processing_jobs.get(job_id)
        if not job:
            return
        job['status'] = 'starting'
        _append_log(job, 'Preparing to process video...')

        if job.get('cancel_requested'):
            job['status'] = 'cancelled'
            _append_log(job, 'Processing cancelled before start.')
            return

    processor = VideoProcessor(job['video_path'], app.config['OUTPUT_FOLDER'])

    def should_cancel():
        with jobs_lock:
            current_job = processing_jobs.get(job_id)
            if not current_job:
                return True
            return bool(current_job.get('cancel_requested'))

    def progress_callback(event):
        with jobs_lock:
            job = processing_jobs.get(job_id)
            if not job:
                return

            event_type = event.get('type')

            if event_type == 'started':
                job['status'] = 'running'
                job['total_frames'] = event.get('total_frames', 0)
                job['fps'] = event.get('fps')
                job['video_id'] = event.get('video_id', job.get('video_id'))
                # Ensure the UI shows immediate progress movement by setting
                # a tiny initial percent when processing starts. This helps
                # the frontend show the progress bar moving right away.
                job['percent_complete'] = job.get('percent_complete') or 0.5
                _append_log(job, 'Video properties loaded. Processing started.')
            elif event_type == 'progress':
                frames = event.get('frames_processed', 0)
                total = event.get('total_frames', job.get('total_frames') or 1)
                percent = event.get('percent_complete')
                if percent is None:
                    percent = round((frames / total) * 100, 2) if total else 0
                job['frames_processed'] = frames
                job['total_frames'] = total
                job['percent_complete'] = percent
                _append_log(job, f"Processed {frames} / {total} frames ({percent:.2f}%)")
            elif event_type == 'slide':
                frame = event.get('frame')
                timestamp = event.get('timestamp')
                extract_preview = event.get('extract')
                time_str = f"{timestamp:.2f}s" if isinstance(timestamp, (int, float)) else "timestamp unavailable"
                _append_log(job, f"Captured slide at frame {frame} ({time_str})")
                if extract_preview:
                    _add_extract(job, {
                        'frame': frame,
                        'timestamp': timestamp,
                        'text': extract_preview,
                    })
            elif event_type == 'preview':
                image_path = event.get('image_path')
                frame = event.get('frame')
                timestamp = event.get('timestamp')
                if image_path and os.path.exists(image_path):
                    job['preview_image_path'] = image_path
                    job['preview_frame'] = frame
                    job['preview_timestamp'] = timestamp
                    job['preview_updated_at'] = time.time()
                    time_str = f"{timestamp:.2f}s" if isinstance(timestamp, (int, float)) else "timestamp unavailable"
                    _append_log(job, f"Preview updated at frame {frame} ({time_str})")
            elif event_type == 'status':
                status_message = event.get('message', 'Processing update')
                frame = event.get('frame')
                segment_start = event.get('segment_start')
                # If the event carries a numeric progress, update job percent
                pct = event.get('progress')
                if isinstance(pct, (int, float)):
                    try:
                        # Throttle percent updates to avoid flooding the UI/logs
                        last_ts = job.get('_last_progress_ts', 0)
                        last_pct = job.get('percent_complete', 0.0)
                        now_ts = time.time()
                        # only update if enough time passed or percent delta is significant
                        if (now_ts - last_ts) >= PROGRESS_THROTTLE_SECONDS or abs(float(pct) - float(last_pct)) >= PROGRESS_MIN_DELTA:
                            job['percent_complete'] = float(pct)
                            job['_last_progress_ts'] = now_ts
                    except Exception:
                        pass
                # If frames/total provided, update frames_processed/total_frames
                if event.get('frames') is not None:
                    try:
                        job['frames_processed'] = int(event.get('frames'))
                    except Exception:
                        pass
                if event.get('total_frames') is not None:
                    try:
                        job['total_frames'] = int(event.get('total_frames'))
                    except Exception:
                        pass
                context_bits = []
                if segment_start is not None:
                    context_bits.append(f"segment {segment_start}→{frame}")
                elif frame is not None:
                    context_bits.append(f"frame {frame}")
                # Only occasionally append verbose status messages to job logs to
                # avoid filling the log panel; prefer lightweight percent updates.
                should_log = False
                last_ts = job.get('_last_log_ts', 0)
                now_ts = time.time()
                if (now_ts - last_ts) >= PROGRESS_THROTTLE_SECONDS:
                    should_log = True
                    job['_last_log_ts'] = now_ts

                if should_log:
                    if context_bits:
                        _append_log(job, f"{status_message} ({', '.join(context_bits)})")
                    else:
                        _append_log(job, status_message)
                # If caller provided ffmpeg stderr or extra debug info, surface it in the logs
                ff_stderr = event.get('ffmpeg_stderr')
                if ff_stderr:
                    # Truncate long stderr to avoid huge logs, but keep useful portion
                    truncated = (ff_stderr[:8000] + '...') if len(ff_stderr) > 8000 else ff_stderr
                    _append_log(job, f"ffmpeg: {truncated}")
            elif event_type == 'gpu':
                # Structured GPU diagnostics emitted by GPU-capable extractors
                diag = event.get('diagnostics') or {}
                # store raw diagnostics on the job for UI consumption
                job['gpu_diagnostics'] = diag
                # Do not append GPU diagnostics into the job logs; UI should
                # read `job['gpu_diagnostics']` to render diagnostics separately.
                # NOTE: we intentionally do not append the full diagnostics blob to
                # the job text/log output to avoid flooding the text panel. The
                # raw diagnostics are stored on `job['gpu_diagnostics']` for UI
                # consumption.
            elif event_type == 'text_sample':
                raw_sample = event.get('sample')
                display_sample = raw_sample or '[No text captured]'
                source_frame = event.get('source_frame')
                source_slide_id = event.get('source_slide_id')
                if source_frame is not None:
                    _append_log(job, f"Captured text sample : {display_sample} (from frame {source_frame})")
                    # Increment job-level counters for visibility
                    job['sample_count'] = job.get('sample_count', 0) + 1

                    # If the sample is empty, record and log it explicitly to aid debugging
                    if raw_sample is None or not str(raw_sample).strip():
                        job['empty_samples'] = job.get('empty_samples', 0) + 1
                        _append_log(job, f"Received empty text sample for frame {source_frame}")

                    # Also surface the sample into the extracts panel for immediate UI visibility
                    try:
                        ts = None
                        if job.get('fps') and isinstance(source_frame, (int, float)):
                            ts = round(source_frame / float(job.get('fps')), 2)
                        _add_extract(job, {
                            'frame': source_frame,
                            'timestamp': ts,
                            'text': raw_sample if raw_sample is not None else display_sample,
                        })

                        # Best-effort persistence: try to map frame -> slide and update DB
                        try:
                            from database import get_slide_by_frame, get_text_extract_by_slide, update_text_extract_original_suggested, add_text_extract, add_slide_minimal

                            # If the job has a video_id, try to find slide by frame
                            vid = job.get('video_id')
                            slide = None
                            if vid:
                                slide = get_slide_by_frame(vid, source_frame)

                            if slide:
                                existing = get_text_extract_by_slide(slide['id'])
                                if existing:
                                    persisted_text = raw_sample if raw_sample is not None and str(raw_sample).strip() else (display_sample or '')
                                    update_text_extract_original_suggested(existing['id'], persisted_text, existing['suggested_text'] or persisted_text)
                                    _append_log(job, f"Persisted sample to existing slide id={slide['id']}")
                                    job['samples_persisted'] = job.get('samples_persisted', 0) + 1
                                else:
                                    persisted_text = raw_sample if raw_sample is not None and str(raw_sample).strip() else (display_sample or '')
                                    add_text_extract(slide['id'], persisted_text, persisted_text)
                                    _append_log(job, f"Created text_extract for slide id={slide['id']}")
                                    job['samples_persisted'] = job.get('samples_persisted', 0) + 1
                            else:
                                # No slide matched this frame; create a minimal slide and store the sample
                                if vid:
                                    new_slide_id = add_slide_minimal(vid)
                                    persisted_text = raw_sample if raw_sample is not None and str(raw_sample).strip() else (display_sample or '')
                                    add_text_extract(new_slide_id, persisted_text, persisted_text)
                                    _append_log(job, f"No matching slide for frame {source_frame}; created placeholder slide id={new_slide_id} and persisted sample")
                                    job['samples_persisted'] = job.get('samples_persisted', 0) + 1
                                else:
                                    _append_log(job, f"No video_id available to persist sample for frame {source_frame}")
                        except Exception:
                            logging.exception('Failed to persist sample to DB')
                    except Exception:
                        # Best-effort: don't fail the job for UI updates
                        logging.exception('Failed to add text sample to extracts')
                elif source_slide_id is not None:
                    _append_log(job, f"Captured text sample : {display_sample} (from slide {source_slide_id})")
                    try:
                        _add_extract(job, {
                            'frame': None,
                            'timestamp': None,
                            'text': raw_sample if raw_sample is not None else display_sample,
                        })
                        # Persist sample by direct slide id
                        try:
                            from database import get_text_extract_by_slide, update_text_extract_original_suggested, add_text_extract
                            existing = get_text_extract_by_slide(source_slide_id)
                            persisted_text = raw_sample if raw_sample is not None and str(raw_sample).strip() else (display_sample or '')
                            if existing:
                                update_text_extract_original_suggested(existing['id'], persisted_text, existing['suggested_text'] or persisted_text)
                            else:
                                add_text_extract(source_slide_id, persisted_text, persisted_text)
                        except Exception:
                            logging.exception('Failed to persist sample to DB (by slide_id)')
                    except Exception:
                        logging.exception('Failed to add text sample to extracts')
                else:
                    _append_log(job, f"Captured text sample : {display_sample}")
            elif event_type == 'error':
                job['status'] = 'error'
                job['error'] = event.get('message', 'Unknown error')
                _append_log(job, f"Error: {job['error']}")
            elif event_type == 'cancelled':
                job['status'] = 'cancelled'
                job['percent_complete'] = event.get('percent_complete', job.get('percent_complete'))
                _append_log(job, 'Processing stopped by user request.')
            elif event_type == 'complete':
                job['status'] = 'completed'
                job['video_id'] = event.get('video_id')
                job['percent_complete'] = 100.0
                job['frames_processed'] = job.get('total_frames', job.get('frames_processed', 0))
                _append_log(job, 'Processing complete.')

    try:
        processor.process_video(
            settings=job['settings'],
            progress_callback=progress_callback,
            should_cancel=should_cancel,
        )
    except Exception as exc:
        logging.exception("Processing job failed")
        with jobs_lock:
            job = processing_jobs.get(job_id)
            if job:
                job['status'] = 'error'
                job['error'] = str(exc)
                _append_log(job, f"Processing error: {exc}")


def _start_processing_job(video_path, settings):
    job_id = uuid4().hex
    job = {
        'job_id': job_id,
        'video_path': video_path,
        'settings': settings,
        'status': 'queued',
        'created_at': time.time(),
        'frames_processed': 0,
        'total_frames': 0,
        'percent_complete': 0.0,
        'logs': [],
        'extracts': [],
        'video_id': None,
        'error': None,
        'preview_image_path': None,
        'preview_frame': None,
        'preview_timestamp': None,
        'preview_updated_at': None,
        'cancel_requested': False,
    }

    with jobs_lock:
        processing_jobs[job_id] = job

    worker = threading.Thread(target=_run_processing_job, args=(job_id,), daemon=True)
    worker.start()
    return job_id


@app.route('/api/job/<job_id>/samples')
def api_job_samples(job_id):
    """Return recent text samples for a processing job."""
    with jobs_lock:
        job = processing_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': 'Job not found'}), 404
        return jsonify({'success': True, 'samples': job.get('extracts', [])})


@app.route('/audio-failures')
def audio_failures_page():
    """Render a page showing recent audio extraction failures with filtering and purge.

    Query params supported:
      - tool: filter by failing tool (e.g., 'ffmpeg', 'moviepy', 'whisper')
      - video_id: filter by video id
      - q: generic search applied to stderr and details
    """
    tool = request.args.get('tool')
    q = request.args.get('q')
    video_id = request.args.get('video_id')
    try:
        vid = int(video_id) if video_id else None
    except Exception:
        vid = None

    failures = get_audio_failures(limit=500, video_id=vid)
    # Apply simple in-memory filters for tool and search for simplicity
    out = []
    for f in failures:
        if tool and str(f['tool'] or '').lower() != str(tool).lower():
            continue
        if q:
            hay = ' '.join([str(f.get('stderr') or ''), str(f.get('details') or ''), str(f.get('error_message') or '')]).lower()
            if q.lower() not in hay:
                continue
        out.append(f)

    return render_template('audio_failures.html', failures=out, filter_tool=tool, filter_q=q, filter_video_id=video_id)


@app.route('/admin/purge_audio_failures', methods=['POST'])
def admin_purge_audio_failures():
    """Purge audio failures older than N days. Returns JSON with number deleted."""
    days = int(request.form.get('days', 30))
    from database import purge_audio_failures_older_than
    try:
        deleted = purge_audio_failures_older_than(days)
        flash(f"Purged {deleted} audio failures older than {days} days", 'success')
        return redirect(url_for('audio_failures_page'))
    except Exception as e:
        logging.exception('Failed to purge audio failures')
        flash('Failed to purge audio failures: ' + str(e), 'error')
        return redirect(url_for('audio_failures_page'))


@app.route('/api/audio_failures')
def api_audio_failures():
    limit = int(request.args.get('limit', 200))
    video_id = request.args.get('video_id')
    try:
        vid = int(video_id) if video_id else None
    except Exception:
        vid = None
    failures = get_audio_failures(limit=limit, video_id=vid)
    # Convert sqlite.Row to dicts
    out = []
    for f in failures:
        out.append({
            'id': f['id'],
            'video_id': f['video_id'],
            'filename': f['filename'],
            'slide_id': f['slide_id'],
            'start_frame': f['start_frame'],
            'end_frame': f['end_frame'],
            'attempts': f['attempts'],
            'error_message': f['error_message'],
            'tool': f.get('tool'),
            'stderr': f.get('stderr'),
            'details': f.get('details'),
            'created_at': f['created_at'],
        })
    return jsonify({'success': True, 'failures': out})


@app.route('/audio-failures/<int:failure_id>')
def audio_failure_detail(failure_id):
    # Direct DB access to fetch one failure
    from database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT af.*, v.filename FROM audio_failures af LEFT JOIN videos v ON v.id = af.video_id WHERE af.id = ?', (failure_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        abort(404)
    return render_template('audio_failure_detail.html', failure=row)


@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'video' not in request.files:
        return jsonify({'success': False, 'message': 'No video file provided.'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type.'}), 400

    original_filename = secure_filename(file.filename)
    unique_name = f"{uuid4().hex}_{original_filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(filepath)

    # Try to extract first frame as a quick preview image (non-blocking best-effort)
    preview_url = None
    try:
        import cv2
        cap = cv2.VideoCapture(filepath)
        ret, frame = cap.read()
        cap.release()
        if ret and frame is not None:
            preview_filename = f'preview_{uuid4().hex}.jpg'
            preview_path = os.path.join(app.config.get('OUTPUT_FOLDER', 'output'), preview_filename)
            try:
                cv2.imwrite(preview_path, frame)
                preview_url = url_for('output_file', filename=preview_filename)
            except Exception:
                logging.exception('Failed to write preview image')
    except Exception:
        logging.exception('Failed to extract preview frame (ignored)')

    try:
        properties = _normalize_properties(get_video_properties(filepath))
    except ImportError as e:
        logging.exception('Failed to get video properties due to missing dependency')
        return jsonify({'success': False, 'message': str(e)}), 500

    file_id = uuid4().hex
    uploaded_files[file_id] = {
        'path': filepath,
        'original_name': original_filename,
        'properties': properties,
    }

    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': original_filename,
        'properties': properties,
        'preview_url': preview_url,
    })


def _parse_settings(data):
    settings = data.get('settings', {}) if isinstance(data, dict) else {}

    def _cast(key, cast_type, default):
        value = settings.get(key, default)
        try:
            return cast_type(value)
        except (TypeError, ValueError):
            return default

    result = {
        'extraction_method': settings.get('extraction_method', 'default'),
        'threshold_ssim': _cast('threshold_ssim', float, 0.9),
        'threshold_hist': _cast('threshold_hist', float, 0.9),
        'frame_gap': _cast('frame_gap', int, 10),
        'transition_limit': _cast('transition_limit', int, 3),
        'progress_interval': _cast('progress_interval', int, 25),
        'preview_interval': _cast('preview_interval', int, PREVIEW_FRAME_INTERVAL),
        'force_slide_interval': _cast('force_slide_interval', int, PREVIEW_FRAME_INTERVAL),
        'histogram_bins': _cast('histogram_bins', int, 256),
        'scale_percent': _cast('scale_percent', float, 100.0),
        'target_resolution_percent': _cast('target_resolution_percent', float, 100.0),
        'whisper_model': settings.get('whisper_model', 'base'),
        'audio_retry_attempts': _cast('audio_retry_attempts', int, 3),
        'audio_skip_on_failure': bool(settings.get('audio_skip_on_failure', True)),
        'summary_min_length': _cast('summary_min_length', int, 30),
        'summary_max_length': _cast('summary_max_length', int, 150),
        'summary_model': settings.get('summary_model', 'sshleifer/distilbart-cnn-12-6'),
        'katna_max_keyframes': _cast('katna_max_keyframes', int, 0),
        'katna_scale_percent': _cast('katna_scale_percent', float, 50.0),
        'min_slide_audio_seconds': _cast('min_slide_audio_seconds', float, 0.0),
        'auto_benchmark': bool(settings.get('auto_benchmark', False)),
    }

    # Merge any additional keys provided directly by the user in `settings` so
    # that test helpers and other extensions may pass-through values like
    # 'test_slides' without changing the code that constructs settings.
    if isinstance(settings, dict):
        for k, v in settings.items():
            if k not in result:
                result[k] = v

    return result


@app.route('/api/job/<job_id>/cancel', methods=['POST'])
def api_cancel_job(job_id):
    with jobs_lock:
        job = processing_jobs.get(job_id)
        if not job:
            return jsonify({'success': False, 'message': 'Job not found.'}), 404

        if job.get('status') in {'completed', 'error', 'cancelled'}:
            return jsonify({'success': False, 'message': 'Job is no longer running.'}), 400

        job['cancel_requested'] = True
        job['status'] = 'cancelling'
        _append_log(job, 'Cancellation requested by user...')

    return jsonify({'success': True})


@app.route('/api/process', methods=['POST'])
def api_process():
    data = request.get_json() or {}
    file_id = data.get('file_id')
    if not file_id or file_id not in uploaded_files:
        return jsonify({'success': False, 'message': 'Unknown or missing file reference.'}), 400

    settings = _parse_settings(data)
    # Pass-through additional top-level keys (useful for test overrides like 'test_slides')
    for k, v in data.items():
        if k not in ('file_id', 'settings') and k not in settings:
            settings[k] = v

    file_entry = uploaded_files[file_id]
    job_id = _start_processing_job(file_entry['path'], settings)

    # Return which method and file are being used so the UI can display it immediately
    extraction_method = settings.get('extraction_method', 'default')
    original_name = file_entry.get('original_name') or os.path.basename(file_entry.get('path'))

    return jsonify({'success': True, 'job_id': job_id, 'method': extraction_method, 'filename': original_name})


@app.route('/api/progress/<job_id>', methods=['GET'])
def api_progress(job_id):
    try:
        with jobs_lock:
            job = processing_jobs.get(job_id)

        if not job:
            return jsonify({'success': False, 'message': 'Job not found.'}), 404

        snapshot = deepcopy(job)
        snapshot['logs'] = list(snapshot['logs'])
        snapshot['extracts'] = list(snapshot['extracts'])

        preview_path = snapshot.get('preview_image_path')
        if preview_path:
            cache_source = snapshot.get('preview_updated_at') or time.time()
            cache_bust = int(cache_source * 1000)
            snapshot['preview_image_url'] = url_for('job_preview_image', job_id=job_id) + f'?t={cache_bust}'
        snapshot.pop('preview_image_path', None)

        if snapshot.get('video_id'):
            snapshot['edit_url'] = url_for('edit_video', video_id=snapshot['video_id'])
            snapshot['review_url'] = url_for('review_video', video_id=snapshot['video_id'])

        # If worker hasn't set percent_complete yet, derive it from frames_processed
        try:
            pct = snapshot.get('percent_complete')
            frames = int(snapshot.get('frames_processed') or 0)
            total = int(snapshot.get('total_frames') or 0)
            if (pct is None or float(pct) == 0.0) and total > 0 and frames > 0:
                try:
                    snapshot['percent_complete'] = round((frames / float(total)) * 100.0, 2)
                except Exception:
                    pass
        except Exception:
            pass

        snapshot.setdefault('gpu_diagnostics', {})

        return jsonify({'success': True, 'job': snapshot})
    except Exception as e:
        # Ensure we never return an empty response; log the error and return JSON
        logging.exception('Failed to build job progress snapshot')
        try:
            return jsonify({'success': False, 'message': f'Internal error: {str(e)}'}), 500
        except Exception:
            # As a last resort, return a simple string with 500
            return ('Internal server error', 500)


@app.route('/api/job/<job_id>/preview')
def job_preview_image(job_id):
    with jobs_lock:
        job = processing_jobs.get(job_id)

    if not job:
        return jsonify({'success': False, 'message': 'Job not found.'}), 404

    image_path = job.get('preview_image_path')
    if not image_path or not os.path.exists(image_path):
        return jsonify({'success': False, 'message': 'Preview not available.'}), 404

    response = send_file(image_path, mimetype='image/jpeg')
    response.headers['Cache-Control'] = 'no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/output/<path:filename>')
def output_file(filename):
    """Serve files from the output folder so templates can reference /output/<name> directly."""
    output_dir = app.config.get('OUTPUT_FOLDER', 'output')
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(output_dir, filename)


@app.route('/wav/<path:filename>')
def wav_file(filename):
    wav_dir = os.path.join(os.getcwd(), 'wav')
    file_path = os.path.join(wav_dir, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(wav_dir, filename)


@app.route('/api/_health')
@app.route('/api/health')
def api_health():
    """Return JSON status of key runtime dependencies and system tools."""
    import shutil
    status = {}

    # System tools
    status['ffprobe'] = bool(shutil.which('ffprobe'))
    status['ffmpeg'] = bool(shutil.which('ffmpeg'))

    # Python packages
    pkgs = {}
    try:
        import cv2
        pkgs['opencv'] = True
    except Exception:
        pkgs['opencv'] = False
    try:
        import sqlalchemy
        pkgs['sqlalchemy'] = True
    except Exception:
        pkgs['sqlalchemy'] = False
    try:
        import reportlab
        pkgs['reportlab'] = True
    except Exception:
        pkgs['reportlab'] = False
    try:
        import whisper
        pkgs['whisper'] = True
    except Exception:
        pkgs['whisper'] = False

    status['packages'] = pkgs

    # Overall OK if required pieces are present
    status['ok'] = status['ffprobe'] and pkgs['sqlalchemy'] and pkgs['reportlab']
    status['time'] = time.time()

    return jsonify(status)


@app.route('/api/debug_job/<job_id>')
def api_debug_job(job_id):
    """Return a small debug snapshot for a job."""
    with jobs_lock:
        job = processing_jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'message': 'Job not found.'}), 404
    snapshot = {
        'job_id': job.get('job_id'),
        'status': job.get('status'),
        'percent_complete': job.get('percent_complete'),
        'frames_processed': job.get('frames_processed'),
        'total_frames': job.get('total_frames'),
        'logs_count': len(job.get('logs', [])),
        'gpu_diagnostics': job.get('gpu_diagnostics'),
        'error': job.get('error'),
    }
    snapshot.setdefault('gpu_diagnostics', {})

    return jsonify({'success': True, 'job': snapshot})


@app.route('/api/job/<job_id>/logs')
def api_job_logs(job_id):
    """Return last N log entries for a job and optionally host logs.

    Query params:
      - n: number of job log entries to return (default 50)
      - host: if '1' and app.config['LOG_FILE'] set, returns last N lines from that file
    """
    n = int(request.args.get('n', 50))
    include_host = request.args.get('host') == '1'

    with jobs_lock:
        job = processing_jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'message': 'Job not found.'}), 404

    logs = list(job.get('logs', []))[-n:]

    response = {'success': True, 'job_id': job_id, 'logs': logs}

    if include_host:
        log_file = app.config.get('LOG_FILE')
        host_lines = []
        if log_file and os.path.exists(log_file):
            try:
                # Read last N lines from the host log file efficiently
                with open(log_file, 'rb') as f:
                    f.seek(0, os.SEEK_END)
                    filesize = f.tell()
                    block_size = 1024
                    blocks = []
                    remaining = n
                    # Read backwards in blocks until we have enough lines or reach start
                    while filesize > 0 and len(blocks) < 64:
                        read_size = min(block_size, filesize)
                        f.seek(filesize - read_size)
                        block = f.read(read_size)
                        blocks.insert(0, block)
                        filesize -= read_size
                    data = b''.join(blocks).decode('utf-8', errors='replace')
                    host_lines = data.strip().splitlines()[-n:]
            except Exception:
                logging.exception('Failed to read host log file')
        response['host_log_lines'] = host_lines

    return jsonify(response)


@app.route('/api/jobs')
def api_jobs():
    """List current in-memory processing jobs. Optional filter: video_id"""
    video_id = request.args.get('video_id')
    try:
        vid = int(video_id) if video_id else None
    except Exception:
        vid = None
    out = []
    with jobs_lock:
        for jid, job in processing_jobs.items():
            if vid and job.get('video_id') != vid:
                continue
            out.append({'job_id': jid, 'video_id': job.get('video_id'), 'status': job.get('status'), 'percent_complete': job.get('percent_complete')})
    return jsonify({'success': True, 'jobs': out})


@app.route('/api/job/<job_id>/stream')
def api_job_stream(job_id):
    """Server-Sent Events stream for job logs. Clients can connect to receive live
    job logs and status updates in real time.

    Usage: GET /api/job/<job_id>/stream
    """
    def event_stream():
        last_index = 0
        while True:
            with jobs_lock:
                job = processing_jobs.get(job_id)
                if not job:
                    yield 'event: error\n'
                    yield 'data: Job not found\n\n'
                    return
                logs = job.get('logs', [])
                status = job.get('status')
            # Send any new logs
            while last_index < len(logs):
                entry = logs[last_index]
                msg = f"[{entry.get('timestamp')}] {entry.get('message')}"
                yield f'data: {msg}\n\n'
                last_index += 1
            # Send periodic heartbeat/status
            yield f'data: [status] {status}\n\n'
            if status in ('completed', 'error', 'cancelled') and last_index >= len(logs):
                return
            import time
            time.sleep(0.5)

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/slide_wav/<int:slide_id>')
def api_slide_wav(slide_id):
    """Return a URL to the wav file for a given slide if it exists."""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        # Get slide and video
        cur.execute('SELECT s.id AS sid, s.video_id, s.frame_number, v.filename FROM slides s JOIN videos v ON v.id = s.video_id WHERE s.id = ?', (slide_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'Slide not found'}), 404
        video_id = row['video_id']
        frame = row['frame_number']
        filename = row['filename']
        # find previous slide frame
        cur.execute('SELECT frame_number FROM slides WHERE video_id = ? AND frame_number < ? ORDER BY frame_number DESC LIMIT 1', (video_id, frame))
        prev = cur.fetchone()
        conn.close()
        prev_frame = prev['frame_number'] if prev else 1

        base_name = os.path.splitext(os.path.basename(filename))[0]

        # 1) deterministic pattern from config
        pattern = app.config.get('WAV_FILENAME_PATTERN')
        if pattern:
            candidate_rel = pattern.format(video_id=video_id, base=base_name, prev=prev_frame, frame=frame)
            candidate_path = os.path.join(os.getcwd(), 'wav', candidate_rel)
            if os.path.exists(candidate_path):
                logging.info(f"Found wav by pattern for slide {slide_id}: {candidate_rel}")
                url = url_for('wav_file', filename=candidate_rel)
                return jsonify({'success': True, 'wav_url': url})

        # 2) root wav folder candidate: wav/<base>-<prev>-<frame>.wav
        candidate_rel2 = f"{base_name}-{prev_frame}-{frame}.wav"
        candidate_path2 = os.path.join(os.getcwd(), 'wav', candidate_rel2)
        if os.path.exists(candidate_path2):
            logging.info(f"Found wav for slide {slide_id}: {candidate_rel2}")
            url = url_for('wav_file', filename=candidate_rel2)
            return jsonify({'success': True, 'wav_url': url})

        # 3) fallback: search wav directory (and subfolders) for files matching pattern base-*-frame.wav
        import glob
        search_pattern = os.path.join(os.getcwd(), 'wav', '**', f"{base_name}-*-{frame}.wav")
        matches = glob.glob(search_pattern, recursive=True)
        if matches:
            # prefer shortest relative path
            chosen = matches[0]
            # convert absolute path to relative under wav/ for url_for
            rel = os.path.relpath(chosen, os.path.join(os.getcwd(), 'wav'))
            logging.info(f"Found wav by glob for slide {slide_id}: {rel}")
            url = url_for('wav_file', filename=rel)
            return jsonify({'success': True, 'wav_url': url})

        return jsonify({'success': False, 'message': 'Wav not found'}), 404
    except Exception as e:
        logging.exception('Failed to locate slide wav')
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
