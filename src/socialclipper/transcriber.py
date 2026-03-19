"""Transcribe video audio using mlx-whisper (Apple Silicon optimized)."""

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """Extract audio from video as WAV for Whisper."""
    audio_path = output_dir / "audio.wav"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # 16-bit PCM (Whisper's preferred format)
        "-ar", "16000",           # 16kHz sample rate
        "-ac", "1",               # mono
        str(audio_path),
        "-y",                     # overwrite
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr.strip()}")
    return audio_path


def transcribe(video_path: Path, model_name: str = "small",
               on_progress=None) -> dict:
    """Transcribe video using mlx-whisper.

    Returns dict with:
        - "text": full transcript
        - "segments": list of {"start", "end", "text"} dicts
    """
    if on_progress:
        on_progress("Extracting audio...")

    audio_path = extract_audio(video_path, video_path.parent)

    if on_progress:
        on_progress(f"Transcribing with Whisper ({model_name})... this may take a few minutes")

    try:
        import mlx_whisper
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=f"mlx-community/whisper-{model_name}-mlx",
            word_timestamps=True,
        )
    except ImportError:
        raise RuntimeError(
            "mlx-whisper is not installed. Run: pip install mlx-whisper"
        )

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
    }
