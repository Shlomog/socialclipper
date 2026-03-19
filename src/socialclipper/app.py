"""FastAPI web server with SSE progress updates."""

import asyncio
import json
import os
import queue
import shutil
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from .clipper import extract_clip, get_video_duration
from .downloader import is_url, get_video_title
from .pipeline import run_pipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="SocialClipper")

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory job tracking
jobs: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Job queue — process one video at a time to avoid memory overload
# ---------------------------------------------------------------------------
_job_queue: queue.Queue = queue.Queue()


def _queue_worker():
    """Background thread that pulls jobs and runs them one at a time."""
    while True:
        job_id = _job_queue.get()
        try:
            _run_job(job_id)
        except Exception:
            pass
        finally:
            _job_queue.task_done()


_worker_thread = threading.Thread(target=_queue_worker, daemon=True)
_worker_thread.start()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.get("/processing", response_class=HTMLResponse)
async def processing_page():
    return (STATIC_DIR / "processing.html").read_text()


@app.post("/api/start")
async def start_job(
    url: str = Form(default=None),
    file: UploadFile | None = File(default=None),
    context: str = Form(default=""),
    max_clips: int = Form(default=4),
):
    """Start a new processing job. Accepts either a URL or file upload."""
    if not url and not file:
        return JSONResponse({"error": "Provide a URL or upload a file"}, status_code=400)

    job_id = str(uuid.uuid4())[:8]

    # If file uploaded, save it
    source = None
    if file and file.filename:
        upload_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
        source = str(upload_path)
    elif url:
        source = url.strip()

    jobs[job_id] = {
        "status": "queued",
        "source": source,
        "source_name": None,
        "context": context.strip() or None,
        "max_clips": max_clips,
        "progress": [],
        "result": None,
        "error": None,
    }

    # Add to sequential queue (one at a time to avoid memory overload)
    _job_queue.put(job_id)

    return {"job_id": job_id}


def _run_job(job_id: str):
    """Run the pipeline synchronously (called from executor)."""
    job = jobs[job_id]
    job["status"] = "running"

    # Resolve video title early so the Processing page can show it immediately
    source = job["source"]
    if source and is_url(source):
        try:
            job["source_name"] = get_video_title(source)
        except Exception:
            job["source_name"] = None
    elif source:
        job["source_name"] = Path(source).stem
    else:
        job["source_name"] = None

    def on_progress(msg: str):
        job["progress"].append(msg)

    try:
        result = run_pipeline(
            source=job["source"],
            output_base=OUTPUT_DIR,
            context=job["context"],
            max_clips=job["max_clips"],
            on_progress=on_progress,
        )
        job["result"] = result
        job["status"] = "done"
    except Exception as e:
        job["error"] = str(e)
        job["status"] = "error"
        job["progress"].append(f"Error: {e}")


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs and their status."""
    return {
        jid: {
            "status": j["status"],
            "source": j.get("source", ""),
            "source_name": j.get("source_name"),
            "progress": j["progress"],
            "error": j["error"],
            "result": j.get("result"),
        }
        for jid, j in jobs.items()
    }


@app.get("/api/status/{job_id}")
async def job_status(job_id: str):
    """Poll job status and progress."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    return {
        "status": job["status"],
        "source_name": job.get("source_name"),
        "progress": job["progress"],
        "result": job["result"],
        "error": job["error"],
    }


@app.get("/api/stream/{job_id}")
async def stream_progress(job_id: str):
    """SSE stream of progress updates."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    async def event_generator():
        last_index = 0
        while True:
            # Send new progress messages
            current = job["progress"]
            if len(current) > last_index:
                for msg in current[last_index:]:
                    yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"
                last_index = len(current)

            # Check if done
            if job["status"] == "done":
                yield f"data: {json.dumps({'type': 'done', 'result': job['result']})}\n\n"
                break
            elif job["status"] == "error":
                yield f"data: {json.dumps({'type': 'error', 'error': job['error']})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/clip/{job_id}/{filename}")
async def get_clip(job_id: str, filename: str):
    """Download a single clip video file."""
    job = jobs.get(job_id)
    if not job or not job["result"]:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    clip_path = Path(job["result"]["output_dir"]) / "clips" / filename
    if not clip_path.exists():
        return JSONResponse({"error": "Clip not found"}, status_code=404)

    return FileResponse(
        str(clip_path),
        media_type="video/mp4",
        filename=filename,
    )


@app.get("/api/download-all/{job_id}")
async def download_all(job_id: str):
    """Download a zip of all clips and drafts."""
    job = jobs.get(job_id)
    if not job or not job["result"]:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    output_dir = Path(job["result"]["output_dir"])
    zip_path = output_dir / "all_clips.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add clips
        clips_dir = output_dir / "clips"
        if clips_dir.exists():
            for f in clips_dir.iterdir():
                if f.suffix == ".mp4":
                    zf.write(f, f"clips/{f.name}")
        # Add drafts
        drafts_file = output_dir / "drafts.md"
        if drafts_file.exists():
            zf.write(drafts_file, "drafts.md")

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"socialclipper_{job_id}.zip",
    )


# ---------------------------------------------------------------------------
# Library — browse all past results
# ---------------------------------------------------------------------------
@app.get("/library", response_class=HTMLResponse)
async def library_page():
    return (STATIC_DIR / "library.html").read_text()


@app.get("/api/library")
async def library_list():
    """List all past output folders with their analysis data."""
    results = []
    if not OUTPUT_DIR.exists():
        return {"results": results}

    for folder in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        # Skip archived folders
        if (folder / ".archived").exists():
            continue
        analysis_file = folder / "analysis.json"
        if not analysis_file.exists():
            continue
        try:
            analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Extract source video name from folder: YYYYMMDD_HHMMSS_<video_title>
        parts = folder.name.split("_", 2)
        source_name = parts[2] if len(parts) >= 3 else folder.name

        # Count clips
        clips_dir = folder / "clips"
        clip_files = sorted(clips_dir.glob("*.mp4")) if clips_dir.exists() else []

        # Read drafts
        drafts = []
        for i, clip in enumerate(analysis.get("clips", []), 1):
            platform = clip.get("platform", "linkedin")
            clip_filename = f"clip_{i}_{platform}.mp4"
            has_video = (clips_dir / clip_filename).exists() if clips_dir.exists() else False

            drafts.append({
                "index": i,
                "title": clip.get("title", f"Clip {i}"),
                "platform": platform,
                "platform_name": "LinkedIn" if platform == "linkedin" else "Instagram Reel",
                "content_type": clip.get("content_type", ""),
                "brand_pillar": clip.get("brand_pillar", ""),
                "start_time": clip.get("start_time", 0),
                "end_time": clip.get("end_time", 0),
                "transcript_excerpt": clip.get("transcript_excerpt", ""),
                "video_file": clip_filename if has_video else None,
            })

        # Check if source video is available for editing
        has_source = (folder / "source.mp4").exists()

        # Get source video duration for the trim UI
        source_duration = None
        if has_source:
            try:
                source_duration = get_video_duration(folder / "source.mp4")
            except Exception:
                pass

        results.append({
            "folder": folder.name,
            "source_name": source_name,
            "summary": analysis.get("full_summary", ""),
            "key_themes": analysis.get("key_themes", []),
            "clip_count": len(clip_files),
            "drafts": drafts,
            "has_source": has_source,
            "source_duration": source_duration,
        })

    return {"results": results}


@app.get("/api/library/{folder_name}/clip/{filename}")
async def library_clip(folder_name: str, filename: str):
    """Serve a clip from a past output folder."""
    clip_path = OUTPUT_DIR / folder_name / "clips" / filename
    if not clip_path.exists():
        return JSONResponse({"error": "Clip not found"}, status_code=404)
    response = FileResponse(str(clip_path), media_type="video/mp4", filename=filename)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.get("/api/library/{folder_name}/drafts")
async def library_drafts(folder_name: str):
    """Get the drafts.md content for a past output folder."""
    drafts_path = OUTPUT_DIR / folder_name / "drafts.md"
    if not drafts_path.exists():
        return JSONResponse({"error": "Drafts not found"}, status_code=404)
    return {"content": drafts_path.read_text(encoding="utf-8")}


@app.get("/api/library/{folder_name}/download")
async def library_download(folder_name: str):
    """Download a zip of a past output folder."""
    output_dir = OUTPUT_DIR / folder_name
    if not output_dir.exists():
        return JSONResponse({"error": "Folder not found"}, status_code=404)

    zip_path = output_dir / "all_clips.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        clips_dir = output_dir / "clips"
        if clips_dir.exists():
            for f in clips_dir.iterdir():
                if f.suffix == ".mp4":
                    zf.write(f, f"clips/{f.name}")
        drafts_file = output_dir / "drafts.md"
        if drafts_file.exists():
            zf.write(drafts_file, "drafts.md")

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"clips_{folder_name}.zip",
    )


# ---------------------------------------------------------------------------
# Archive — hide old runs from library without deleting files
# ---------------------------------------------------------------------------
@app.post("/api/library/{folder_name}/archive")
async def archive_run(folder_name: str):
    """Archive a run (hides it from the library listing)."""
    folder = OUTPUT_DIR / folder_name
    if not folder.exists():
        return JSONResponse({"error": "Folder not found"}, status_code=404)
    (folder / ".archived").touch()
    return {"ok": True}


@app.post("/api/library/{folder_name}/unarchive")
async def unarchive_run(folder_name: str):
    """Unarchive a run (shows it again in the library listing)."""
    folder = OUTPUT_DIR / folder_name
    archived_marker = folder / ".archived"
    if archived_marker.exists():
        archived_marker.unlink()
    return {"ok": True}


@app.get("/api/library/archived")
async def library_archived_list():
    """List archived output folders (minimal info for the archived tab)."""
    results = []
    if not OUTPUT_DIR.exists():
        return {"results": results}

    for folder in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        if not (folder / ".archived").exists():
            continue
        analysis_file = folder / "analysis.json"
        if not analysis_file.exists():
            continue

        parts = folder.name.split("_", 2)
        source_name = parts[2] if len(parts) >= 3 else folder.name

        clips_dir = folder / "clips"
        clip_count = len(list(clips_dir.glob("*.mp4"))) if clips_dir.exists() else 0

        results.append({
            "folder": folder.name,
            "source_name": source_name,
            "clip_count": clip_count,
        })

    return {"results": results}


# ---------------------------------------------------------------------------
# Clip Editing — Trim + Crop
# ---------------------------------------------------------------------------
@app.get("/api/library/{folder_name}/source")
async def library_source(folder_name: str):
    """Serve the full source video for the edit modal."""
    source_path = OUTPUT_DIR / folder_name / "source.mp4"
    if not source_path.exists():
        return JSONResponse({"error": "Source video not found"}, status_code=404)
    return FileResponse(str(source_path), media_type="video/mp4")


@app.post("/api/library/{folder_name}/edit/{clip_index}")
async def edit_clip(folder_name: str, clip_index: int, request: Request):
    """Re-cut a clip with new start/end times and optional crop position.

    Body JSON: {start_time, end_time, crop_position (optional, 0.0-1.0)}
    """
    folder = OUTPUT_DIR / folder_name
    source_path = folder / "source.mp4"
    analysis_file = folder / "analysis.json"

    if not source_path.exists():
        return JSONResponse({"error": "Source video not found"}, status_code=404)
    if not analysis_file.exists():
        return JSONResponse({"error": "Analysis not found"}, status_code=404)

    body = await request.json()
    new_start = float(body.get("start_time", 0))
    new_end = float(body.get("end_time", 0))
    crop_pos = body.get("crop_position")  # None or 0.0–1.0
    aspect_ratio = body.get("aspect_ratio")  # None or "16:9", "1:1", "9:16"

    if new_end <= new_start:
        return JSONResponse({"error": "End time must be after start time"}, status_code=400)

    # Load analysis
    analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    clips = analysis.get("clips", [])

    if clip_index < 1 or clip_index > len(clips):
        return JSONResponse({"error": "Clip index out of range"}, status_code=404)

    clip_info = clips[clip_index - 1]
    platform = clip_info.get("platform", "linkedin")
    clip_filename = f"clip_{clip_index}_{platform}.mp4"
    clip_path = folder / "clips" / clip_filename

    # Re-extract with new times, optional crop, and optional aspect ratio override
    try:
        extract_clip(
            source_video=source_path,
            start_time=new_start,
            end_time=new_end,
            platform=platform,
            output_path=clip_path,
            pad_seconds=0,
            crop_position=float(crop_pos) if crop_pos is not None else None,
            aspect_ratio=aspect_ratio,
        )
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Update analysis.json with new times, crop_position, and aspect_ratio
    clip_info["start_time"] = new_start
    clip_info["end_time"] = new_end
    if crop_pos is not None:
        clip_info["crop_position"] = float(crop_pos)
    if aspect_ratio is not None:
        clip_info["aspect_ratio"] = aspect_ratio
    analysis_file.write_text(json.dumps(analysis, indent=2), encoding="utf-8")

    return {"ok": True, "clip_file": clip_filename}


def main():
    """Entry point for console script."""
    import uvicorn
    uvicorn.run(
        "socialclipper.app:app",
        host="0.0.0.0",
        port=8000,
        app_dir=str(BASE_DIR / "src"),
    )
