"""Main processing pipeline: download -> transcribe -> analyze -> draft -> clip."""

import shutil
from pathlib import Path

from .downloader import is_url, download_video, get_video_title
from .transcriber import transcribe
from .analyzer import analyze_transcript
from .clipper import extract_clip
from .drafter import generate_drafts
from .output import create_output_folder, save_results


def _min_to_sec(val: float) -> float:
    """Convert a minutes.seconds value (e.g. 14.45 = 14m45s) to total seconds."""
    minutes = int(val)
    frac = val - minutes
    seconds = round(frac * 100)  # 14.45 → .45 → 45 seconds
    return minutes * 60 + seconds


def run_pipeline(
    source: str,
    output_base: Path,
    context: str | None = None,
    max_clips: int = 4,
    platforms: list[str] | None = None,
    whisper_model: str = "small",
    on_progress=None,
) -> dict:
    """Run the full pipeline.

    Args:
        source: Local file path or URL
        output_base: Base directory for output
        context: Optional context about the video
        max_clips: Maximum clips to generate
        platforms: Target platforms (default: linkedin + instagram-reel)
        whisper_model: Whisper model size
        on_progress: Callback function for progress updates

    Returns:
        dict with output_dir, drafts, analysis, clips info
    """
    if platforms is None:
        platforms = ["linkedin", "instagram-reel"]

    def progress(msg):
        if on_progress:
            on_progress(msg)

    # ---------------------------------------------------------------
    # Step 1: Resolve source video
    # ---------------------------------------------------------------
    progress("Step 1/6: Getting video...")

    if is_url(source):
        source_name = get_video_title(source)
        output_dir = create_output_folder(output_base, source_name)
        temp_dir = output_dir / ".temp"
        temp_dir.mkdir(exist_ok=True)
        video_path = download_video(source, temp_dir, on_progress=progress)
        progress(f"Downloaded: {source_name}")
    else:
        video_path = Path(source)
        if not video_path.exists():
            raise FileNotFoundError(f"File not found: {source}")
        source_name = video_path.stem
        output_dir = create_output_folder(output_base, source_name)
        # Copy source to temp so pipeline is self-contained
        temp_dir = output_dir / ".temp"
        temp_dir.mkdir(exist_ok=True)

    # ---------------------------------------------------------------
    # Step 2: Transcribe
    # ---------------------------------------------------------------
    progress("Step 2/6: Transcribing audio...")
    transcript = transcribe(video_path, model_name=whisper_model, on_progress=progress)
    seg_count = len(transcript["segments"])
    duration_min = transcript["segments"][-1]["end"] / 60 if transcript["segments"] else 0
    progress(f"Transcribed: {seg_count} segments, {duration_min:.1f} minutes")

    # ---------------------------------------------------------------
    # Step 3: Analyze with Claude
    # ---------------------------------------------------------------
    progress("Step 3/6: Finding the best clip moments...")
    analysis = analyze_transcript(
        transcript=transcript,
        platforms=platforms,
        max_clips=max_clips,
        context=context,
        on_progress=progress,
    )
    progress(f"Found {len(analysis['clips'])} clip-worthy moments")

    # Sanity check: if any clip is under 5 seconds, timestamps are likely
    # in minutes (e.g., 14.45 = 14min 45sec) instead of seconds.
    for clip_info in analysis["clips"]:
        clip_dur = clip_info["end_time"] - clip_info["start_time"]
        if clip_dur < 5:
            progress("Warning: Detected minute-format timestamps, converting to seconds...")
            for c in analysis["clips"]:
                c["start_time"] = _min_to_sec(c["start_time"])
                c["end_time"] = _min_to_sec(c["end_time"])
            break

    # ---------------------------------------------------------------
    # Step 4: Generate drafts
    # ---------------------------------------------------------------
    progress("Step 4/6: Writing social media drafts...")
    drafts = generate_drafts(analysis, context=context, on_progress=progress)
    progress(f"Generated {len(drafts)} drafts")

    # ---------------------------------------------------------------
    # Step 5: Extract video clips
    # ---------------------------------------------------------------
    progress("Step 5/6: Cutting video clips...")
    clip_files = []
    for i, clip_info in enumerate(analysis["clips"], 1):
        platform = clip_info["platform"]
        clip_filename = f"clip_{i}_{platform}.mp4"
        clip_path = output_dir / "clips" / clip_filename
        try:
            extract_clip(
                source_video=video_path,
                start_time=clip_info["start_time"],
                end_time=clip_info["end_time"],
                platform=platform,
                output_path=clip_path,
            )
            clip_files.append(clip_filename)
            progress(f"Extracted clip {i}/{len(analysis['clips'])}: {clip_filename}")
        except RuntimeError as e:
            progress(f"Warning: Failed to extract clip {i}: {e}")
            clip_files.append(None)

    # ---------------------------------------------------------------
    # Step 6: Save output
    # ---------------------------------------------------------------
    progress("Step 6/6: Saving results...")
    save_results(output_dir, analysis, drafts, transcript, source_name)

    # Keep source video for future editing, then clean up temp
    source_keep = output_dir / "source.mp4"
    if not source_keep.exists() and video_path.exists():
        shutil.copy2(str(video_path), str(source_keep))
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    progress("Done!")

    return {
        "output_dir": str(output_dir),
        "source_name": source_name,
        "summary": analysis.get("full_summary", ""),
        "key_themes": analysis.get("key_themes", []),
        "clips": [
            {
                "index": i + 1,
                "title": drafts[i]["clip_title"],
                "platform": drafts[i]["platform"],
                "platform_name": drafts[i]["platform_name"],
                "content_type": drafts[i]["content_type"],
                "brand_pillar": drafts[i]["brand_pillar"],
                "start_time": drafts[i]["start_time"],
                "end_time": drafts[i]["end_time"],
                "draft_text": drafts[i]["draft_text"],
                "video_file": clip_files[i] if i < len(clip_files) else None,
                "reasoning": drafts[i].get("reasoning", ""),
            }
            for i in range(len(drafts))
        ],
    }
