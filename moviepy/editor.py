"""Compatibility shim to provide `moviepy.editor` namespace expected by older code.

Many codebases import `from moviepy.editor import VideoFileClip` but newer moviepy versions
expose the implementation under `moviepy.video.io.VideoFileClip`. This shim re-exports
commonly used classes to maintain backward compatibility in tests and runtime code.
"""

from moviepy.video.io.VideoFileClip import VideoFileClip
# Re-export common symbols if needed in future
__all__ = ["VideoFileClip"]
