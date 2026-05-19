import os
import re
import time
import uuid
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from .detector import run_detection
from .schemas import UploadResponse, JobStatus, DetectionStats
from .logger import logger

router = APIRouter(prefix="/api")

_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)

_BASE = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(_BASE, "uploads")
OUTPUT_DIR = os.path.join(_BASE, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _make_job_id(filename: str) -> str:
    """Generate a readable job ID: vid_{date}_{time}_{slug}_{suffix}"""
    stem = os.path.splitext(filename or "video")[0]
    slug = re.sub(r"[^a-zA-Z0-9]", "", stem)[:20].lower() or "video"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:4]
    return f"vid_{timestamp}_{slug}_{suffix}"


def _reencode_h264(src: str, dst: str) -> bool:
    import shutil
    import subprocess
    ffmpeg = (shutil.which("ffmpeg") or
              shutil.which("ffmpeg", path="/opt/homebrew/bin:/usr/local/bin:/usr/bin") or
              "/opt/homebrew/bin/ffmpeg")
    if not os.path.exists(ffmpeg):
        logger.warning("ffmpeg not found — skipping H.264 re-encode", event="reencode_skipped")
        return False

    logger.info("Starting H.264 re-encode", event="reencode_start", src=src, dst=dst)
    result = subprocess.run(
        [ffmpeg, "-y", "-i", src, "-vcodec", "libx264", "-crf", "23",
         "-preset", "fast", "-movflags", "+faststart", dst],
        capture_output=True,
    )
    if result.returncode == 0:
        logger.info("H.264 re-encode complete", event="reencode_done", dst=dst)
    else:
        logger.error(
            "H.264 re-encode failed",
            event="reencode_failed",
            stderr=result.stderr.decode(errors="replace")[-500:],
        )
    return result.returncode == 0


def _process_job(job_id: str, input_path: str, output_path: str, filename: str):
    def update_progress(pct: int):
        if job_id in _jobs:
            _jobs[job_id]["progress"] = int(pct * 0.9)

    job_start = time.time()
    try:
        _jobs[job_id]["status"] = "processing"
        logger.info(
            f"Job started — processing video",
            event="job_start",
            job_id=job_id,
            filename=filename,
        )

        raw_path = output_path.replace("_output.mp4", "_raw.mp4")
        detection_start = time.time()
        stats = run_detection(input_path, raw_path, progress_callback=update_progress)
        detection_sec = round(time.time() - detection_start, 1)

        logger.info(
            f"Detection complete — {stats['total_frames']} frames, {stats['total_riders']} riders, "
            f"compliance {stats['compliance_rate']}%",
            event="detection_done",
            job_id=job_id,
            filename=filename,
            duration_seconds=detection_sec,
            total_frames=stats["total_frames"],
            total_riders=stats["total_riders"],
            with_helmet=stats["with_helmet"],
            without_helmet=stats["without_helmet"],
            compliance_rate=stats["compliance_rate"],
        )

        reencoded = _reencode_h264(raw_path, output_path)
        if reencoded:
            os.remove(raw_path)
        else:
            os.rename(raw_path, output_path)

        total_sec = round(time.time() - job_start, 1)
        _jobs[job_id].update({"status": "done", "progress": 100, "stats": stats, "output_path": output_path})

        logger.info(
            f"Job done in {total_sec}s — output ready",
            event="job_done",
            job_id=job_id,
            filename=filename,
            total_duration_seconds=total_sec,
            reencoded=reencoded,
        )

    except Exception as e:
        _jobs[job_id].update({"status": "error", "message": str(e)})
        logger.exception(
            f"Job FAILED — {e}",
            event="job_failed",
            job_id=job_id,
            filename=filename,
            error=str(e),
            duration_seconds=round(time.time() - job_start, 1),
        )
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


# ── POST /api/jobs — upload video and create a job ──────────────────────────
@router.post("/jobs", response_model=UploadResponse)
async def create_job(file: UploadFile = File(...)):
    VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    is_video_mime = file.content_type and file.content_type.startswith("video/")

    if not is_video_mime and ext not in VIDEO_EXTS:
        logger.warning(
            "Rejected upload — not a video file",
            event="upload_rejected",
            filename=file.filename,
            content_type=file.content_type,
        )
        raise HTTPException(status_code=400, detail="Only video files are accepted")

    job_id = _make_job_id(file.filename or "video")
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}_input.mp4")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_output.mp4")

    content = await file.read()
    file_size_mb = round(len(content) / 1024 / 1024, 2)

    with open(input_path, "wb") as f:
        f.write(content)

    _jobs[job_id] = {"status": "queued", "progress": 0, "message": "", "stats": None, "output_path": None}

    logger.info(
        f"Upload accepted — {file.filename} ({file_size_mb} MB) → {job_id}",
        event="upload_accepted",
        job_id=job_id,
        filename=file.filename,
        file_size_mb=file_size_mb,
        content_type=file.content_type,
    )

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _process_job, job_id, input_path, output_path, file.filename)

    return UploadResponse(job_id=job_id)


# ── GET /api/jobs/{job_id} — poll job status ─────────────────────────────────
@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        logger.warning("Status check for unknown job", event="status_not_found", job_id=job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job.get("message", ""),
    )


# ── GET /api/jobs/{job_id}/stats — detection statistics ──────────────────────
@router.get("/jobs/{job_id}/stats", response_model=DetectionStats)
def get_job_stats(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        logger.warning("Stats request for unknown job", event="stats_not_found", job_id=job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        logger.warning(
            "Stats requested but job not complete",
            event="stats_not_ready",
            job_id=job_id,
            current_status=job["status"],
        )
        raise HTTPException(status_code=400, detail="Job not complete yet")

    logger.info("Stats fetched", event="stats_fetched", job_id=job_id)
    return DetectionStats(**job["stats"])


# ── GET /api/jobs/{job_id}/download — stream annotated video ─────────────────
@router.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        logger.warning("Download request for unknown job", event="download_not_found", job_id=job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        logger.warning(
            "Download requested but job not complete",
            event="download_not_ready",
            job_id=job_id,
            current_status=job["status"],
        )
        raise HTTPException(status_code=400, detail="Job not complete yet")

    path = job["output_path"]
    if not path or not os.path.exists(path):
        logger.error(
            "Download failed — output file missing on disk",
            event="download_file_missing",
            job_id=job_id,
            expected_path=path,
        )
        raise HTTPException(status_code=404, detail="Output file not found")

    file_size_mb = round(os.path.getsize(path) / 1024 / 1024, 2)
    logger.info(
        f"Download started — {file_size_mb} MB",
        event="download_started",
        job_id=job_id,
        file_size_mb=file_size_mb,
    )
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
