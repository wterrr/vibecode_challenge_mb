"""API route handlers for job CRUD and video streaming."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.api.schemas import CreateJobResponse, JobResponse, UpdateJobRequest
from app.domain.enums import JobStatus
from app.domain.lesson import LearningRequest
from app.services.job_service import DeleteStatus, JobService
from app.storage.base import ArtifactStore

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_job_service(request: Request) -> JobService:
    """Retrieve JobService instance from app state."""
    return request.app.state.job_service


def get_artifact_store(request: Request) -> ArtifactStore:
    """Retrieve ArtifactStore instance from app state."""
    return request.app.state.artifact_store


@router.post("", response_model=CreateJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: LearningRequest,
    job_service: JobService = Depends(get_job_service),
) -> CreateJobResponse:
    """Create a new educational video job and enqueue for background processing."""
    job = await job_service.create_job(request)
    return CreateJobResponse(
        job_id=job.id,
        status=job.status,
        status_url=f"/api/jobs/{job.id}",
        page_url=f"/jobs/{job.id}",
    )


@router.get("", response_model=list[JobResponse])
def list_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    status: JobStatus | None = Query(default=None),
    job_service: JobService = Depends(get_job_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> list[JobResponse]:
    """List jobs ordered newest-first with optional status filter."""
    jobs = job_service.list_jobs(limit=limit, status=status)
    results = []
    for job in jobs:
        video_url = None
        if job.status == JobStatus.SUCCEEDED:
            final_path = artifact_store.get_final_path(job.id)
            if final_path is not None:
                video_url = f"/api/jobs/{job.id}/video"
        results.append(JobResponse.from_job(job, video_url=video_url))
    return results


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> JobResponse:
    """Retrieve detailed status and metadata of a specific job."""
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    video_url = None
    if job.status == JobStatus.SUCCEEDED:
        final_path = artifact_store.get_final_path(job.id)
        if final_path is not None:
            video_url = f"/api/jobs/{job.id}/video"

    return JobResponse.from_job(job, video_url=video_url)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: str,
    body: UpdateJobRequest,
    job_service: JobService = Depends(get_job_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> JobResponse:
    """Update user-modifiable fields (display_title, note) preserving omitted fields."""
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    fields_set = body.model_fields_set
    new_title = body.display_title if "display_title" in fields_set else job.display_title
    new_note = body.note if "note" in fields_set else job.note

    updated = job_service.update_user_fields(
        job_id,
        display_title=new_title,
        note=new_note,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    video_url = None
    if updated.status == JobStatus.SUCCEEDED:
        final_path = artifact_store.get_final_path(updated.id)
        if final_path is not None:
            video_url = f"/api/jobs/{updated.id}/video"

    return JobResponse.from_job(updated, video_url=video_url)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
) -> Response:
    """Delete completed or failed job and its artifacts; reject queued or running jobs."""
    result = job_service.delete_job(job_id)
    if result.status == DeleteStatus.NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.message or "Job not found",
        )
    if result.status == DeleteStatus.CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.message or "Cannot delete active job",
        )
    if result.status == DeleteStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message or "Failed to delete job artifacts",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}/video")
def get_job_video(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> FileResponse:
    """Stream final MP4 video artifact if job succeeded and artifact exists."""
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )

    if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Video is still being generated",
        )

    if job.status == JobStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job failed; video artifact is not available",
        )

    # Job is SUCCEEDED: must verify published final.mp4
    final_path = artifact_store.get_final_path(job_id)
    if final_path is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Video artifact not found for succeeded job",
        )

    return FileResponse(
        path=final_path,
        media_type="video/mp4",
        filename=f"learnflow_{job_id}.mp4",
    )
