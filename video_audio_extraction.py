# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details

import warnings
# moviepy v1 exposed VideoFileClip under `moviepy.editor`, while newer versions
# expose it under `moviepy.video.io.VideoFileClip`. Support both to be robust
# across environments.
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
    # Import whisper lazily to avoid requiring it at module import time for tests
    try:
        import whisper
    except ModuleNotFoundError as e:
        raise ImportError("Whisper is not installed. Install via 'pip install openai-whisper' or 'pip install -r requirements.txt' (prefer 'openai-whisper' for best compatibility)") from e

    model_size = model_size or "base"
    if model_size not in _WHISPER_MODELS:
        logging.info(f"Loading Whisper model '{model_size}'")
        # Prefer loading the model directly onto CPU if whisper supports the device arg
        try:
            try:
                model = whisper.load_model(model_size, device='cpu')
            except TypeError:
                # Older whisper versions may not accept a device arg
                model = whisper.load_model(model_size)

            # Attempt to move model to CPU and set dtype when torch is available
            try:
                import torch
                cpu = torch.device('cpu')
                # Some model wrappers may not support .to(cpu) or dtype change; wrap safely
                try:
                    model.to(cpu)
                except Exception:
                    logging.debug('Failed to move Whisper model to CPU with .to(cpu)')
                try:
                    model.to(dtype=torch.float32)
                except Exception:
                    # Not all whisper model wrappers support explicit dtype conversion; ignore
                    pass
            except Exception:
                # If torch isn't available or conversion fails, proceed with the loaded model
                logging.debug('torch not available or unable to move Whisper model to CPU/dtype')

            # Only cache the model after successful load
            _WHISPER_MODELS[model_size] = model
            logging.info("Whisper model loaded and moved to CPU (float32 if supported)")
            return _WHISPER_MODELS[model_size]
        except Exception as load_err:
            logging.exception(f"Failed to load Whisper model '{model_size}': {load_err}")
            # Re-raise to allow callers to handle failures (they may fallback)
            raise
    # If model was already cached, return it
    return _WHISPER_MODELS.get(model_size)


def extract_audio_segment(video_path, start_frame, end_frame, fps, output_audio_path, max_attempts: int = None):
    # Calculate start time and duration
    start_time = start_frame / fps
    duration = (end_frame - start_frame) / fps
    # Try ffmpeg first, with a small retry/backoff in case of transient failures
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
            # small backoff before retrying
            import time
            time.sleep(0.6 * attempt)

    # After retries, attempt moviepy fallback
    logging.error(f"ffmpeg failed after {max_attempts} attempts for segment {start_frame}→{end_frame}")
    try:
        from database import add_audio_failure
        stderr_text = last_ffmpeg_stderr or ''
        # write full stderr to logs and store a truncated summary in DB
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
        # Ensure we don't request beyond clip.duration
        clip_start = max(0, min(clip.duration, start_time))
        clip_end = max(0, min(clip.duration, start_time + duration))
        if clip_end <= clip_start:
            raise RuntimeError(f"Invalid subclip range: start={clip_start}, end={clip_end}")
        sub = clip.subclip(clip_start, clip_end)
        # Write as WAV with 16 kHz sample rate and 2 bytes per sample (pcm_s16le)
        sub.audio.write_audiofile(output_audio_path, fps=16000, nbytes=2, codec='pcm_s16le', verbose=False, logger=None)
        # Close readers to avoid file descriptor leaks
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
            from database import add_audio_failure
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
        # Raise a clear error that includes ffmpeg stderr and the fallback message
        raise RuntimeError(
            f"ffmpeg error (after {max_attempts} attempts): {last_ffmpeg_stderr}\nMoviePy fallback error: {me}"
        )

def _cleanup_wav_folder(folder_path: str, max_files: int = 200):
    """Ensure the wav folder doesn't grow beyond max_files by removing the oldest files."""
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
    """Write full ffmpeg stderr to a timestamped file under logs/audio_failures/.

    Returns the path to the written log or None on failure.
    """
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
            # Not critical if chmod fails in some environments
            pass
        # Ensure logs dir is ignored by git
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

    # Support either a full path to the video file (uploads/...) or a bare filename
    base_wav_folder = 'wav'

    # ensure base wav folder exists
    os.makedirs(base_wav_folder, exist_ok=True)

    # If caller passed a path that exists, use it directly; otherwise fall back to videos/ folder
    if os.path.exists(video_file_name):
        video_full_path = video_file_name
    else:
        video_folder = 'videos'
        filename_without_ext = os.path.splitext(os.path.basename(video_file_name))[0]
        video_full_path = os.path.join(video_folder, filename_without_ext + '.mp4')

    logging.info(f"Video file path: {video_full_path}")

    if not os.path.exists(video_full_path):
        raise FileNotFoundError(f"Video file not found: {video_full_path}")

    # Build per-video wav folder when video_id is provided; otherwise use base wav folder
    if video_id:
        wav_folder = os.path.join(base_wav_folder, str(video_id))
    else:
        wav_folder = base_wav_folder

    os.makedirs(wav_folder, exist_ok=True)

    # Build wav output path based on the actual video filename (without extension)
    filename_without_ext = os.path.splitext(os.path.basename(video_full_path))[0]
    wav_full_path = os.path.join(wav_folder, f"{filename_without_ext}-{last_frame_idx}-{frame_idx}.wav")

    logging.info(f"Checking if wav file {wav_full_path} exists")
    if not os.path.exists(wav_full_path):
        logging.info(f"Wav file {wav_full_path} does not exist; extracting audio segment")
        try:
            extract_audio_segment(video_full_path, last_frame_idx, frame_idx, fps, wav_full_path, max_attempts=audio_retry_attempts)
            # Cleanup folder to limit number of stored wav files
            _cleanup_wav_folder(wav_folder, max_files=max_wav_files)
            logging.info(f"Audio segment written to {wav_full_path} (size={os.path.getsize(wav_full_path)} bytes)")
        except Exception as e:
            logging.exception(f"Audio extraction failed for {video_full_path} {last_frame_idx}->{frame_idx}: {e}")
            # Extraction has already recorded a detailed audio_failure (including ffmpeg log path)
            # Allow caller to continue; return empty transcript
            return ""
    else:
        try:
            logging.info(f"Existing wav file found: {wav_full_path} (size={os.path.getsize(wav_full_path)} bytes)")
        except Exception:
            logging.info(f"Existing wav file found: {wav_full_path}")

    # Load the whisper model (may raise). Handle missing dependency explicitly
    logging.info(f"Loading Whisper model '{model_size}' for frames {last_frame_idx}->{frame_idx}")
    try:
        model = _load_whisper_model(model_size)
    except ImportError as ie:
        logging.error(f"Whisper not available: {ie}")
        try:
            from database import add_audio_failure
            add_audio_failure(video_id, None, last_frame_idx, frame_idx, 0, f"Whisper not installed: {ie}", tool='whisper', stderr=str(ie))
        except Exception:
            logging.exception('Failed to record audio_failure for missing Whisper')
        # Return empty transcription so processing continues without crashing
        return ""
    # Whisper may warn about FP16 on CPU; we've ensured the model is on CPU and float32
    # but the library may still emit a benign warning. Suppress that specific warning
    # locally so it doesn't spam logs during processing.
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
                # log a small dump of the wav file size to aid debugging
                wav_size = os.path.getsize(wav_full_path)
                logging.debug(f"WAV size: {wav_size} bytes for {wav_full_path}")
            except Exception:
                pass
            return ""
        logging.info(f"Recognized text for frames {last_frame_idx}->{frame_idx} (duration={duration:.2f}s): {recognized_text[:240]!s}")
        return recognized_text
    except Exception as e:
        # Log and record an audio_failure if a video_id is provided so operators can inspect
        import logging as _logging
        _err_text = str(e)
        _logging.exception(f"Whisper transcription failed for {wav_full_path}: {_err_text}")
        try:
            from database import add_audio_failure
            # Use provided audio_retry_attempts as attempts if available
            attempts = int(audio_retry_attempts) if audio_retry_attempts is not None else 0
            # Truncate stderr to a reasonable length to avoid huge DB fields
            stderr_trunc = (_err_text[:4000] + '...') if len(_err_text) > 4000 else _err_text
            add_audio_failure(video_id, None, last_frame_idx, frame_idx, attempts, f"Whisper error (refer to stderr)", tool='whisper', stderr=stderr_trunc)
        except Exception:
            _logging.exception('Failed to record audio_failure after transcription error')
        # Return empty string to allow processing to continue without crashing
        return ""

@lru_cache(maxsize=4)
def _get_summarizer(model_name: str = "sshleifer/distilbart-cnn-12-6"):
    """Lazy import of transformers.pipeline with a compatibility shim.

    Some torchvision/torch combinations expect torch.library.register_fake to exist
    at import-time which can raise AttributeError during eager imports. To avoid
    breaking the whole application on import, patch a no-op register_fake (safe)
    before importing transformers.pipeline.
    """
    # Best-effort compatibility shim for environments where torch.library lacks register_fake
    try:
        import torch
        if hasattr(torch, 'library') and not hasattr(torch.library, 'register_fake'):
            def _register_fake(name):
                def decorator(fn):
                    return fn
                return decorator
            try:
                # Try to attach directly if possible
                setattr(torch.library, 'register_fake', _register_fake)
            except Exception:
                # Fallback: insert a shim module into sys.modules so imports that
                # access 'torch.library' find an object with register_fake
                import types, sys
                mod = types.ModuleType('torch.library')
                mod.register_fake = _register_fake
                sys.modules.setdefault('torch.library', mod)
    except Exception:
        # If anything goes wrong here, continue and let the real import raise a clear error
        pass

    # Import lazily after applying the shim
    try:
        from transformers import pipeline
        # If torch with CUDA is available, pass the device argument so the pipeline
        # runs on GPU. Otherwise pipeline will default to CPU.
        try:
            import torch
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                device_arg = 0  # first GPU
            else:
                device_arg = -1  # CPU
        except Exception:
            device_arg = -1

        # Attempt to construct the pipeline (this may download and load model weights)
        if device_arg == -1:
            return pipeline("summarization", model=model_name)
        else:
            return pipeline("summarization", model=model_name, device=device_arg)
    except Exception as e:
        # If HF transformers or the model cannot be loaded (torch/version issues, network,
        # or safety checks), fall back to a safe, deterministic summarizer that won't
        # crash the worker. We detect the specific ValueError raised when
        # transformers refuses to use `torch.load` due to the CVE mitigation (requires
        # torch>=2.6) and emit an explicit, actionable message instructing the user
        # to either upgrade torch or use safetensors for model weights.
        import logging
        logging.exception("Failed to create transformers summarization pipeline; using fallback summarizer: %s", e)

        # Detect the well-known transformers safety check message around torch.load
        _err_text = str(e) or ""
        _is_torch_load_vuln = False
        try:
            if isinstance(e, ValueError):
                low = _err_text.lower()
                if 'torch.load' in low or 'vulnerab' in low or 'cve-2025' in low or '>=2.6' in low or '>= 2.6' in low or 'requires torch' in low:
                    _is_torch_load_vuln = True
        except Exception:
            _is_torch_load_vuln = False

        if _is_torch_load_vuln:
            guidance = (
                "Transformers refused to load model weights using torch.load due to a "
                "security mitigation (CVE-2025-32434). To enable HF model loading you must "
                "upgrade PyTorch to >=2.6 or use safetensors-based model files. "
                "See: https://nvd.nist.gov/vuln/detail/CVE-2025-32434"
            )
            logging.error(guidance)
        else:
            guidance = None

        def _fallback_summarizer(text, **kwargs):
            # kwargs may include max_length/min_length; approximate characters per token
            max_length = int(kwargs.get('max_length', 150) or 150)
            approx_chars = max(64, max_length * 4)
            s = str(text).strip()
            if not s:
                # Return the same shape; include short guidance if this was the CVE case
                if guidance:
                    return [{'summary_text': '', 'note': guidance}]
                return [{'summary_text': ''}]
            if len(s) <= approx_chars:
                if guidance:
                    return [{'summary_text': s, 'note': guidance}]
                return [{'summary_text': s}]
            # Try to cut at word boundary for nicer output
            part = s[:approx_chars]
            if ' ' in part:
                part = part.rsplit(' ', 1)[0]
            out = {'summary_text': part + '...'}
            if guidance:
                out['note'] = guidance
            return [out]

        return _fallback_summarizer


def summrise_text(
    text,
    *,
    max_length: int = 150,
    min_length: int = 30,
    model_name: str = "sshleifer/distilbart-cnn-12-6",
):
    """Summarise text with configurable parameters."""

    summarizer = _get_summarizer(model_name)
    max_length = max(max_length, min_length + 5)
    summarized_text = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summarized_text
