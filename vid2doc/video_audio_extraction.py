"""Audio extraction and transcription helpers (moved into package).

This module mirrors the original `video_audio_extraction.py` implementation
and is intended to be the canonical location for imports once the project
fully migrates into the `vid2doc` package.
"""
import warnings
try:
    from moviepy.editor import VideoFileClip
except Exception:
    from moviepy.video.io.VideoFileClip import VideoFileClip

import os
from pydub import AudioSegment
import logging
import ffmpeg
from io import BytesIO
from functools import lru_cache
import pathlib
import datetime
import uuid
import json


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

_WHISPER_MODELS = {}


def _load_whisper_model(model_size: str):
    """Lazy-load and cache Whisper models to avoid repeated downloads.

    Raises ImportError with a clear message if the `whisper` package is missing so
    callers can handle the missing dependency gracefully.
    """
    try:
        import whisper
    except ModuleNotFoundError as e:
        raise ImportError("Whisper is not installed. Install via 'pip install openai-whisper' or 'pip install -r requirements.txt' (prefer 'openai-whisper' for best compatibility)") from e

    model_size = model_size or "base"
    if model_size not in _WHISPER_MODELS:
        logging.info(f"Loading Whisper model '{model_size}'")
        try:
            try:
                model = whisper.load_model(model_size, device='cpu')
            except TypeError:
                model = whisper.load_model(model_size)

            try:
                import torch
                cpu = torch.device('cpu')
                try:
                    model.to(cpu)
                except Exception:
                    logging.debug('Failed to move Whisper model to CPU with .to(cpu)')
                try:
                    model.to(dtype=torch.float32)
                except Exception:
                    pass
            except Exception:
                logging.debug('torch not available or unable to move Whisper model to CPU/dtype')

            _WHISPER_MODELS[model_size] = model
            logging.info("Whisper model loaded and moved to CPU (float32 if supported)")
            return _WHISPER_MODELS[model_size]
        except Exception as load_err:
            logging.exception(f"Failed to load Whisper model '{model_size}': {load_err}")
            raise
    return _WHISPER_MODELS.get(model_size)


def extract_audio_segment(video_path, start_frame, end_frame, fps, output_audio_path, max_attempts: int = None):
    start_time = start_frame / fps
    duration = (end_frame - start_frame) / fps
    if max_attempts is None:
        max_attempts = 3
    attempt = 0
    last_ffmpeg_stderr = None
    while attempt < max_attempts:
        attempt += 1
        try:
            (
                ffmpeg
                .input(video_path, ss=start_time, t=duration)
                .output(output_audio_path)
                .global_args('-hide_banner')
                .run(capture_stdout=True, capture_stderr=True)
            )
            logging.info(
                f"Audio segment extracted from {start_frame} to {end_frame} and saved to {output_audio_path} (attempt {attempt})"
            )
            return
        except ffmpeg.Error as e:
            try:
                last_ffmpeg_stderr = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, (bytes, bytearray)) else str(e.stderr)
            except Exception:
                last_ffmpeg_stderr = str(e)
            logging.warning(
                f"ffmpeg attempt {attempt} failed for segment {start_frame}→{end_frame}: {last_ffmpeg_stderr}"
            )
            import time
            time.sleep(0.6 * attempt)

    logging.error(f"ffmpeg failed after {max_attempts} attempts for segment {start_frame}→{end_frame}")
    try:
        from vid2doc.database import add_audio_failure
        stderr_text = last_ffmpeg_stderr or ''
        try:
            log_path = _write_ffmpeg_log(stderr_text, video_id=None, prefix=os.path.splitext(os.path.basename(output_audio_path))[0])
        except Exception:
            log_path = None
        stderr_trunc = (stderr_text[:2000] + '...(truncated)') if len(stderr_text) > 2000 else stderr_text
        details = json.dumps({'ffmpeg_log_path': log_path}) if log_path else None
        add_audio_failure(None, None, start_frame, end_frame, max_attempts, f"ffmpeg error: {stderr_trunc}", tool='ffmpeg', stderr=stderr_trunc, details=details)
    except Exception:
        logging.exception('Failed to record ffmpeg audio_failure (ignored)')

    logging.info("Attempting moviepy fallback for audio extraction")
    try:
        clip = VideoFileClip(video_path)
        clip_start = max(0, min(clip.duration, start_time))
        clip_end = max(0, min(clip.duration, start_time + duration))
        if clip_end <= clip_start:
            raise RuntimeError(f"Invalid subclip range: start={clip_start}, end={clip_end}")
        sub = clip.subclip(clip_start, clip_end)
        sub.audio.write_audiofile(output_audio_path, fps=16000, nbytes=2, codec='pcm_s16le', verbose=False, logger=None)
        try:
            clip.reader.close()
        except Exception:
            pass
        try:
            clip.audio.reader.close_proc()
        except Exception:
            pass

        logging.info(f"Fallback extraction succeeded and saved to {output_audio_path}")
        return
    except Exception as me:
        logging.error(f"MoviePy fallback also failed: {me}")
        try:
            from vid2doc.database import add_audio_failure
            stderr_text = str(me) or ''
            try:
                log_path = _write_ffmpeg_log(stderr_text, video_id=None, prefix=os.path.splitext(os.path.basename(output_audio_path))[0])
            except Exception:
                log_path = None
            stderr_trunc = (stderr_text[:2000] + '...(truncated)') if len(stderr_text) > 2000 else stderr_text
            details = json.dumps({'ffmpeg_log_path': log_path}) if log_path else None
            add_audio_failure(None, None, start_frame, end_frame, max_attempts, f"MoviePy fallback error: {stderr_trunc}", tool='moviepy', stderr=stderr_trunc, details=details)
        except Exception:
            logging.exception('Failed to record moviepy audio_failure (ignored)')
        raise RuntimeError(
            f"ffmpeg error (after {max_attempts} attempts): {last_ffmpeg_stderr}\nMoviePy fallback error: {me}"
        )


def _cleanup_wav_folder(folder_path: str, max_files: int = 200):
    try:
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        if len(files) <= max_files:
            return
        files.sort(key=lambda p: os.path.getmtime(p))
        to_remove = files[: max(0, len(files) - max_files)]
        for f in to_remove:
            try:
                os.remove(f)
            except Exception:
                logging.exception(f"Failed to remove old wav file: {f}")
    except Exception:
        logging.exception("Failed to cleanup wav folder")


def _write_ffmpeg_log(stderr_text: str, video_id: int = None, prefix: str = None) -> str | None:
    try:
        logs_dir = os.path.join('logs', 'audio_failures')
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        safe_prefix = (prefix or 'ffmpeg').replace(' ', '_')
        vid = str(video_id) if video_id is not None else 'nogid'
        filename = f"{vid}_{safe_prefix}_{timestamp}_{uuid.uuid4().hex[:8]}.stderr.log"
        path = os.path.join(logs_dir, filename)
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(stderr_text or '')
        try:
            os.chmod(path, 0o640)
        except Exception:
            pass
        gi = os.path.join(logs_dir, '.gitignore')
        if not os.path.exists(gi):
            try:
                with open(gi, 'w') as g:
                    g.write('*\n')
            except Exception:
                pass
        return path
    except Exception:
        logging.exception('Failed to write ffmpeg stderr log')
        return None


def get_slide_text(video_file_name, last_frame_idx, frame_idx, fps, *, model_size: str = "base", audio_retry_attempts: int = None, video_id: int = None, max_wav_files: int = 200):

    base_wav_folder = 'wav'
    os.makedirs(base_wav_folder, exist_ok=True)

    if os.path.exists(video_file_name):
        video_full_path = video_file_name
    else:
        video_folder = 'videos'
        filename_without_ext = os.path.splitext(os.path.basename(video_file_name))[0]
        video_full_path = os.path.join(video_folder, filename_without_ext + '.mp4')

    logging.info(f"Video file path: {video_full_path}")

    if not os.path.exists(video_full_path):
        raise FileNotFoundError(f"Video file not found: {video_full_path}")

    if video_id:
        wav_folder = os.path.join(base_wav_folder, str(video_id))
    else:
        wav_folder = base_wav_folder

    os.makedirs(wav_folder, exist_ok=True)

    filename_without_ext = os.path.splitext(os.path.basename(video_full_path))[0]
    wav_full_path = os.path.join(wav_folder, f"{filename_without_ext}-{last_frame_idx}-{frame_idx}.wav")

    logging.info(f"Checking if wav file {wav_full_path} exists")
    if not os.path.exists(wav_full_path):
        logging.info(f"Wav file {wav_full_path} does not exist; extracting audio segment")
        try:
            extract_audio_segment(video_full_path, last_frame_idx, frame_idx, fps, wav_full_path, max_attempts=audio_retry_attempts)
            _cleanup_wav_folder(wav_folder, max_files=max_wav_files)
            logging.info(f"Audio segment written to {wav_full_path} (size={os.path.getsize(wav_full_path)} bytes)")
        except Exception as e:
            logging.exception(f"Audio extraction failed for {video_full_path} {last_frame_idx}->{frame_idx}: {e}")
            return ""
    else:
        try:
            logging.info(f"Existing wav file found: {wav_full_path} (size={os.path.getsize(wav_full_path)} bytes)")
        except Exception:
            logging.info(f"Existing wav file found: {wav_full_path}")

    logging.info(f"Loading Whisper model '{model_size}' for frames {last_frame_idx}->{frame_idx}")
    try:
        model = _load_whisper_model(model_size)
    except ImportError as ie:
        logging.error(f"Whisper not available: {ie}")
        try:
            from vid2doc.database import add_audio_failure
            add_audio_failure(video_id, None, last_frame_idx, frame_idx, 0, f"Whisper not installed: {ie}", tool='whisper', stderr=str(ie))
        except Exception:
            logging.exception('Failed to record audio_failure for missing Whisper')
        return ""

    import warnings as _warnings
    import time as _time
    try:
        t0 = _time.time()
        with _warnings.catch_warnings():
            _warnings.filterwarnings('ignore', message='FP16 is not supported on CPU; using FP32 instead')
            result = model.transcribe(wav_full_path)
        duration = _time.time() - t0
        recognized_text = result.get("text", "") if isinstance(result, dict) else str(result)
        if not recognized_text or not recognized_text.strip():
            logging.warning(f"Whisper transcribed empty text for {wav_full_path} (frames {last_frame_idx}->{frame_idx}) [duration={duration:.2f}s]")
            try:
                wav_size = os.path.getsize(wav_full_path)
                logging.debug(f"WAV size: {wav_size} bytes for {wav_full_path}")
            except Exception:
                pass
            return ""
        logging.info(f"Recognized text for frames {last_frame_idx}->{frame_idx} (duration={duration:.2f}s): {recognized_text[:240]!s}")
        return recognized_text
    except Exception as e:
        import logging as _logging
        _err_text = str(e)
        _logging.exception(f"Whisper transcription failed for {wav_full_path}: {_err_text}")
        try:
            from vid2doc.database import add_audio_failure
            attempts = int(audio_retry_attempts) if audio_retry_attempts is not None else 0
            stderr_trunc = (_err_text[:4000] + '...') if len(_err_text) > 4000 else _err_text
            add_audio_failure(video_id, None, last_frame_idx, frame_idx, attempts, f"Whisper error (refer to stderr)", tool='whisper', stderr=stderr_trunc)
        except Exception:
            _logging.exception('Failed to record audio_failure after transcription error')
        return ""


@lru_cache(maxsize=4)
def _get_summarizer(model_name: str = "sshleifer/distilbart-cnn-12-6"):
    try:
        import torch
        if hasattr(torch, 'library') and not hasattr(torch.library, 'register_fake'):
            def _register_fake(name):
                def decorator(fn):
                    return fn
                return decorator
            try:
                setattr(torch.library, 'register_fake', _register_fake)
            except Exception:
                import types, sys
                mod = types.ModuleType('torch.library')
                mod.register_fake = _register_fake
                sys.modules.setdefault('torch.library', mod)
    except Exception:
        pass

    try:
        from transformers import pipeline
        try:
            import torch
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                device_arg = 0
            else:
                device_arg = -1
        except Exception:
            device_arg = -1

        if device_arg == -1:
            return pipeline("summarization", model=model_name)
        else:
            return pipeline("summarization", model=model_name, device=device_arg)
    except Exception as e:
        import logging
        logging.exception("Failed to create transformers summarization pipeline; using fallback summarizer: %s", e)
        _err_text = str(e) or ""
        _is_torch_load_vuln = False
        try:
            if isinstance(e, ValueError):
                low = _err_text.lower()
                if 'torch.load' in low or 'vulnerab' in low or 'cve-2025' in low or '>=2.6' in low or '>= 2.6' in low or 'requires torch' in low:
                    _is_torch_load_vuln = True
        except Exception:
            pass

        def fallback_summarizer(texts, **kwargs):
            if isinstance(texts, str):
                texts = [texts]
            return [
                {'summary_text': (t[:400] + '...' if len(t) > 400 else t)} for t in texts
            ]

        return fallback_summarizer
