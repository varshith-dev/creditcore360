from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from shared.job_queue import job_queue
from shared.models import JobType, JobStatus

logger = logging.getLogger(__name__)

jobs_router = APIRouter()

class CreateJobRequest(BaseModel):
    job_type: JobType
    job_data: Dict[str, Any]
    user_id: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    progress: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    tasks: List[Dict[str, Any]] = []

@jobs_router.post("/jobs/start")
async def start_job(request: CreateJobRequest):
    """Start a new background job"""
    try:
        logger.info(f"Starting job of type {request.job_type.value}")
    return job_store

@jobs_router.delete("/jobs/{job_id}")
async def delete_job(job_id: str = Path(..., description="Job ID")):
    """Delete a job from the store"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    del job_store[job_id]
    logger.info(f"Deleted job: {job_id}")
    
    return {"message": f"Job {job_id} deleted successfully"}

def update_job_progress(job_id: str, stage: JobStage, progress_pct: float, error_message: str = None):
    """Update job progress (called by background tasks)"""
    if job_id in job_store:
        job = job_store[job_id]
        job.stage = stage
        job.progress_pct = progress_pct
        if error_message:
            job.error_message = error_message
            job.status = JobStatus.FAILED
            job.completed_at = asyncio.get_event_loop().time()
        elif progress_pct >= 100:
            job.status = JobStatus.COMPLETED
            job.completed_at = asyncio.get_event_loop().time()
        else:
            job.status = JobStatus.RUNNING
        
        logger.info(f"Updated job {job_id}: stage={stage}, progress={progress_pct}%")
