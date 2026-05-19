from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued | processing | done | error
    progress: int
    message: str


class DetectionStats(BaseModel):
    total_frames: int
    standalone_persons: int
    standalone_motorcycles: int
    total_riders: int
    with_helmet: int
    without_helmet: int
    compliance_rate: Optional[float]
