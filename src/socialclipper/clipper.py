"""Extract video clips with ffmpeg, formatted per platform."""

import subprocess
from pathlib import Path

from .config import PLATFORM_SPECS


ASPECT_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "9:16": (1080, 1920),
}


def _build_crop_vf(platform: str, crop_position: float, aspect_ratio: str | None = None) -> str:
    """Build an ffmpeg -vf string that crops (instead of padding) to fill the frame.

    crop_position: 0.0 = left/top edge, 0.5 = center, 1.0 = right/bottom edge
    aspect_ratio: optional override like "9:16", "1:1", "16:9"
    """
    if aspect_ratio and aspect_ratio in ASPECT_RESOLUTIONS:
        tw, th = ASPECT_RESOLUTIONS[aspect_ratio]
    else:
        spec = PLATFORM_SPECS[platform]
        w, h = spec["resolution"].split("x")
        tw, th = int(w), int(h)

    target_ratio = tw / th
    cp = max(0.0, min(1.0, crop_position))

    if target_ratio > 1:
        # Target is landscape: crop height, keep full width
        crop = f"crop=iw:iw*{th}/{tw}:0:(ih-iw*{th}/{tw})*{cp}"
    elif target_ratio < 1:
        # Target is portrait: crop width, keep full height
        crop = f"crop=ih*{tw}/{th}:ih:(iw-ih*{tw}/{th})*{cp}:0"
    else:
        # Target is square: crop to the smaller dimension
        crop = f"crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))*{cp}:(ih-min(iw\\,ih))*{cp}"

    return f"{crop},scale={tw}:{th}"


def extract_clip(
    source_video: Path,
    start_time: float,
    end_time: float,
    platform: str,
    output_path: Path,
    pad_seconds: float = 0.5,
    crop_position: float | None = None,
    aspect_ratio: str | None = None,
) -> Path:
    """Extract a clip and format it for the target platform.

    Adds padding before/after for natural transitions.
    Applies platform-specific scaling/aspect ratio.

    If crop_position is provided (0.0-1.0), crops instead of padding
    to fill the frame without black bars.
    If aspect_ratio is provided (e.g. "9:16"), overrides the platform default.
    """
    spec = PLATFORM_SPECS[platform]

    padded_start = max(0, start_time - pad_seconds)
    padded_end = end_time + pad_seconds
    duration = padded_end - padded_start

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use crop filter when crop_position specified or aspect ratio overridden
    if aspect_ratio and aspect_ratio in ASPECT_RESOLUTIONS:
        # Aspect ratio override always uses crop (default center if no crop_position)
        vf = _build_crop_vf(platform, crop_position if crop_position is not None else 0.5, aspect_ratio)
    elif crop_position is not None:
        vf = _build_crop_vf(platform, crop_position)
    else:
        vf = spec["ffmpeg_vf"]

    cmd = [
        "ffmpeg",
        "-ss", str(padded_start),
        "-i", str(source_video),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[:300]}")

    return output_path


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return float(result.stdout.strip())
