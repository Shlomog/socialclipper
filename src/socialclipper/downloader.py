"""Download videos from YouTube and social media URLs via yt-dlp."""

import subprocess
from pathlib import Path


def is_url(source: str) -> bool:
    """Check if source looks like a URL."""
    return source.strip().startswith(("http://", "https://", "www."))


def download_video(url: str, output_dir: Path, on_progress=None) -> Path:
    """Download video from URL using yt-dlp.

    Returns path to the downloaded MP4 file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "source_video.%(ext)s")

    cmd = [
        "yt-dlp",
        "--format",
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]"
        "/best[height<=1080][ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--output", output_template,
        "--no-playlist",
        "--restrict-filenames",
        "--newline",  # one progress line per update
        url,
    ]

    if on_progress:
        on_progress("Downloading video...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.strip()}")

    # Find the output file
    for f in output_dir.iterdir():
        if f.name.startswith("source_video") and f.suffix in (".mp4", ".mkv", ".webm"):
            return f

    raise RuntimeError("Download completed but output file not found")


def get_video_title(url: str) -> str:
    """Get the title of a video from its URL."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--no-playlist", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "video"
