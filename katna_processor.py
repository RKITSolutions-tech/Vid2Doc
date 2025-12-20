# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details
#
# NOTE: This module integrates with Katna (GPL-3.0 licensed).
# When you use this module, your usage must comply with Katna's GPL-3.0 license.
# The Katna extraction method is optional - the core system works without it.

"""Katna keyframe helper - minimal, stable implementation.

CPU-first: scales a video via ffmpeg (libx264) and runs Katna keyframe
extraction. This file is intentionally small and robust for the test
environment. It purposely avoids enabling GPU ffmpeg variants here to
keep behavior deterministic in CI and on varied hosts.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
import shutil
from typing import Callable, List, Optional, Tuple
import logging


logger = logging.getLogger(__name__)

try:
    import katna
except Exception:
    katna = None

# Tunable encoder settings (can be overridden via environment variables)
NVENC_PRESET = os.getenv("KATNA_NVENC_PRESET", "p1")
CPU_PRESET = os.getenv("KATNA_CPU_PRESET", "ultrafast")
CPU_CRF = os.getenv("KATNA_CPU_CRF", "23")


ProgressCallback = Optional[Callable[[str, float], None]]


def _safe_report(cb: ProgressCallback, event: str, progress: float) -> None:
    """Call progress callback in a tolerant way.

    Accepts either callback(event, progress) or callback(event_dict).
    Any exceptions raised by the user callback are swallowed to avoid
    breaking the extraction pipeline.
    """
    if not cb:
        return
    try:
        # Preferred form: callback(event, progress)
        cb(event, progress)
        return
    except TypeError:
        # Fallback: callback with a single dict argument
        try:
            cb({"event": event, "progress": progress})
            return
        except Exception:
            return
    except Exception:
        # User callback raised an unexpected exception; ignore it.
        return


def _probe_resolution(path: str) -> Tuple[int, int]:
    """Return (width, height) for the first video stream using ffprobe.

    Raises RuntimeError on failure.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffprobe failed: " + (p.stderr or p.stdout or ""))
    parts = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    if len(parts) >= 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            pass
    raise RuntimeError("Could not determine video resolution from ffprobe output")


def _create_scaled_video_cpu(input_path: str, scale_percent: int) -> str:
    """Create a temporay scaled MP4 using ffmpeg (libx264). Returns path.

    The caller is responsible for deleting the returned file.
    """
    width, height = _probe_resolution(input_path)
    target_w = max(16, int(width * scale_percent / 100.0))
    target_h = max(16, int(height * scale_percent / 100.0))

    fd, out_path = tempfile.mkstemp(suffix=".mp4", prefix="katna_scaled_")
    os.close(fd)

    vf = f"scale={target_w}:{target_h},format=yuv420p"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "23",
        out_path,
    ]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(out_path):
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        raise RuntimeError("ffmpeg scaling failed: " + (p.stderr or p.stdout or ""))

    return out_path


def _ffmpeg_supports_scale_npp() -> bool:
    """Return True if ffmpeg has the scale_npp filter available."""
    try:
        p = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True, timeout=10)
        ok = "scale_npp" in (p.stdout or "")
        logger.debug("ffmpeg scale_npp available: %s", ok)
        return ok
    except Exception:
        return False


def _ffmpeg_supports_nvenc() -> bool:
    """Return True if ffmpeg has NVENC encoders available (h264_nvenc or hevc_nvenc)."""
    try:
        p = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=10)
        out = p.stdout or ""
        ok = "h264_nvenc" in out or "hevc_nvenc" in out
        logger.debug("ffmpeg nvenc available: %s", ok)
        return ok
    except Exception:
        return False


def _run_ffmpeg_command(cmd: List[str], stderr_log_prefix: str = "ffmpeg_err_") -> subprocess.CompletedProcess:
    """Run ffmpeg command and return CompletedProcess. On failure write stderr to a temp log."""
    logger.debug("Running ffmpeg command: %s", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 and p.stderr:
        try:
            fd, path = tempfile.mkstemp(prefix=stderr_log_prefix, suffix=".log")
            os.close(fd)
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                f.write(p.stderr)
        except Exception:
            path = ""
        # attach path attribute for callers to inspect
        p.log_path = path
    else:
        p.log_path = ""
    return p


def _create_scaled_video_gpu(input_path: str, scale_percent: int) -> str:
    """Attempt to scale using GPU-accelerated ffmpeg (scale_npp + NVENC).

    Raises RuntimeError on failure with a reference to the ffmpeg stderr log.
    """
    width, height = _probe_resolution(input_path)
    target_w = max(16, int(width * scale_percent / 100.0))
    target_h = max(16, int(height * scale_percent / 100.0))

    fd, out_path = tempfile.mkstemp(suffix=".mp4", prefix="katna_scaled_")
    os.close(fd)

    # Use scale_npp (NPP) and NVENC encoder when available. Use format=nv12 for NVENC.
    vf = f"scale_npp={target_w}:{target_h},format=nv12"
    cmd = [
        "ffmpeg",
        "-y",
        "-hwaccel",
        "cuda",
        "-i",
        input_path,
        "-vf",
        vf,
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p1",
        out_path,
    ]

    logger.info("Attempting GPU-accelerated ffmpeg scaling (scale_npp + nvenc) to %dx%d", target_w, target_h)
    p = _run_ffmpeg_command(cmd, stderr_log_prefix="ffmpeg_cuda_err_")
    if p.returncode != 0 or not os.path.exists(out_path):
        # Clean up incomplete file
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
    log_path = getattr(p, "log_path", "") or ""
    logger.warning("GPU ffmpeg scaling failed; stderr log: %s", log_path)
    raise RuntimeError(f"GPU ffmpeg scaling failed; stderr_log={log_path}")

    return out_path


def _benchmark_scalers(input_path: str, scale_percent: int, secs: int = 3) -> str:
    """Run short trials of GPU and CPU scalers and return chosen method: 'gpu'|'cpu'.

    If GPU or NVENC not available, returns 'cpu'.
    """
    gpu_ok = _ffmpeg_supports_scale_npp() and _ffmpeg_supports_nvenc()
    if not gpu_ok:
        return "cpu"

    # Create temporary output files for short test runs (-t secs)
    fd1, out_cpu = tempfile.mkstemp(suffix=".mp4", prefix="katna_bench_cpu_")
    os.close(fd1)
    fd2, out_gpu = tempfile.mkstemp(suffix=".mp4", prefix="katna_bench_gpu_")
    os.close(fd2)

    logger.info("Running auto-benchmark for scalers (cpu vs gpu) for %ds", secs)
    try:
        # CPU trial
        vf_cpu = None  # None means use same CPU path but limited duration
        cmd_cpu = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-t",
            str(secs),
            "-vf",
            f"scale={max(16, int(_probe_resolution(input_path)[0] * scale_percent / 100.0))}:{max(16, int(_probe_resolution(input_path)[1] * scale_percent / 100.0))},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            out_cpu,
        ]
        t0 = time.time()
        p_cpu = _run_ffmpeg_command(cmd_cpu, stderr_log_prefix="ffmpeg_bench_cpu_")
        t_cpu = time.time() - t0

        # GPU trial
        vf_gpu = f"scale_npp={max(16, int(_probe_resolution(input_path)[0] * scale_percent / 100.0))}:{max(16, int(_probe_resolution(input_path)[1] * scale_percent / 100.0))},format=nv12"
        cmd_gpu = [
            "ffmpeg",
            "-y",
            "-hwaccel",
            "cuda",
            "-i",
            input_path,
            "-t",
            str(secs),
            "-vf",
            vf_gpu,
            "-c:v",
            "h264_nvenc",
            out_gpu,
        ]
        t0 = time.time()
        p_gpu = _run_ffmpeg_command(cmd_gpu, stderr_log_prefix="ffmpeg_bench_gpu_")
        t_gpu = time.time() - t0
        # Prefer whichever finished faster and succeeded
        gpu_ok_final = (getattr(p_gpu, "returncode", 1) == 0)
        cpu_ok_final = (getattr(p_cpu, "returncode", 1) == 0)
        logger.info("Benchmark results: cpu_ok=%s time=%.2fs, gpu_ok=%s time=%.2fs", cpu_ok_final, t_cpu, gpu_ok_final, t_gpu)
        if gpu_ok_final and (not cpu_ok_final or t_gpu < t_cpu):
            logger.info("Auto-benchmark selected GPU scaler")
            return "gpu"
        logger.info("Auto-benchmark selected CPU scaler")
        return "cpu"
    finally:
        for p in (out_cpu, out_gpu):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def _create_scaled_video(input_path: str, scale_percent: int, prefer_gpu: bool = True, auto_benchmark: bool = False, force_gpu: bool = False) -> str:
    """Create a scaled video, attempting GPU first (or auto-benchmarked) then falling back to CPU.

    prefer_gpu: if True, will try GPU path when available.
    auto_benchmark: if True, run short trials to pick the fastest approach.
    """
    # If no scaling requested, return original path
    if scale_percent >= 100:
        return input_path

    gpu_available = _ffmpeg_supports_scale_npp() and _ffmpeg_supports_nvenc()
    logger.debug("GPU available: %s", gpu_available)

    chosen = "cpu"
    if auto_benchmark and gpu_available:
        try:
            chosen = _benchmark_scalers(input_path, scale_percent)
        except Exception:
            chosen = "cpu"
    else:
        # If force_gpu is requested and GPU is available, choose GPU now
        if force_gpu and gpu_available:
            logger.info("Force-GPU requested and GPU is available — selecting GPU scaler")
            chosen = "gpu"
        elif prefer_gpu and gpu_available:
            chosen = "gpu"
        else:
            chosen = "cpu"

    logger.info("Chosen scaler: %s", chosen)
    if chosen == "gpu":
        try:
            return _create_scaled_video_gpu(input_path, scale_percent)
        except Exception as e:
            # fall back to CPU but keep diagnostic info in the message
            # if the caller wants to investigate they can inspect exception
            logger.warning("Falling back to CPU scaler due to GPU error: %s", e)
            try:
                return _create_scaled_video_cpu(input_path, scale_percent)
            except Exception:
                logger.error("Both GPU and CPU ffmpeg scaling failed")
                raise RuntimeError(f"Both GPU and CPU ffmpeg scaling failed: {e}")
    else:
        logger.info("Using CPU ffmpeg scaler (libx264)")
        return _create_scaled_video_cpu(input_path, scale_percent)


class KatnaKeyframeExtractor:
    """Small wrapper around Katna.KeyframeExtractor that supports optional scaling.

    The constructor accepts an optional video_path and temp_dir to match
    the test expectations and make the class easier to use in callers.
    """

    def __init__(self, video_path: Optional[str] = None, temp_dir: Optional[str] = None) -> None:
        # Allow construction even if Katna is not installed. Fail later when
        # attempting to extract keyframes so callers can inspect attributes in
        # environments without Katna.
        self.video_path = video_path
        self.temp_dir = temp_dir
        self._katna_available = katna is not None

    def extract_keyframes(
        self,
        input_path: str,
        output_dir: str,
        scale_percent: int = 100,
        progress_callback: ProgressCallback = None,
        prefer_gpu: bool = True,
        auto_benchmark: bool = False,
        force_gpu: bool = False,
        **katna_kwargs,
    ) -> List[str]:
        os.makedirs(output_dir, exist_ok=True)

        temp_scaled: Optional[str] = None
        scaled_path = input_path

        if 1 <= scale_percent < 100:
            if progress_callback:
                _safe_report(progress_callback, "scaling", 0.0)
            # Use the new scaler which will attempt GPU (if available) and
            # optionally auto-benchmark or force GPU; falls back to CPU on failure.
            temp_scaled = _create_scaled_video(
                input_path,
                scale_percent,
                prefer_gpu=prefer_gpu,
                auto_benchmark=auto_benchmark,
                force_gpu=force_gpu,
            )
            scaled_path = temp_scaled
            if progress_callback:
                _safe_report(progress_callback, "scaling", 1.0)

        if not self._katna_available:
            raise RuntimeError("Katna library is not available")

        # Some Katna distributions expose different APIs. Prefer the
        # historical KeyframeExtractor when present, otherwise fall back
        # to the Video API which returns frames that we can write to disk.
        import importlib

        if hasattr(katna, "KeyframeExtractor"):
            extractor = katna.KeyframeExtractor()
            # Forward any katna-specific kwargs (e.g., max_keyframes) to katna
            keyframes = extractor.extract_keyframes(scaled_path, output_dir, **katna_kwargs)
        else:
            # Fallback: use Katna.video.Video to extract frames and write them
            # to disk using Katna.writer.KeyFrameDiskWriter so callers receive
            # a list of file paths similar to the primary path above.
            try:
                video_mod = importlib.import_module("Katna.video")
                writer_mod = importlib.import_module("Katna.writer")
            except Exception as e:
                raise RuntimeError(f"Katna package present but required submodules are missing: {e}")

            # Respect an explicit None (meaning 'no limit') passed through
            # by callers. If max_keyframes is None or not provided, default
            # to 5 keyframes for the fallback Video API.
            mk = katna_kwargs.get("max_keyframes", katna_kwargs.get("no_of_frames", None))
            # Treat None or non-positive values as 'use fallback default'
            try:
                if mk is None:
                    no_of_frames = 5
                else:
                    mk_int = int(mk)
                    no_of_frames = 5 if mk_int <= 0 else mk_int
            except Exception:
                no_of_frames = 5
            v = video_mod.Video()
            frames = v._extract_keyframes_from_video(no_of_frames, scaled_path)

            # Write frames to disk
            writer = writer_mod.KeyFrameDiskWriter(output_dir, file_ext=".jpg")
            writer.write(scaled_path, frames)

            # Build returned file list (KeyFrameDiskWriter uses generate_output_filename)
            keyframes = []
            for i in range(len(frames)):
                fname = writer.generate_output_filename(scaled_path, keyframe_number=i) + ".jpg"
                keyframes.append(os.path.join(output_dir, fname))

        if temp_scaled and os.path.exists(temp_scaled):
            try:
                os.remove(temp_scaled)
            except Exception:
                pass

        return keyframes


def extract_keyframes_katna(
    input_path: str,
    output_dir: str,
    scale_percent: int = 100,
    progress_callback: ProgressCallback = None,
    **katna_kwargs,
) -> List[str]:
    extractor = KatnaKeyframeExtractor()
    return extractor.extract_keyframes(
        input_path,
        output_dir,
        scale_percent=scale_percent,
        progress_callback=progress_callback,
        **katna_kwargs,
    )
