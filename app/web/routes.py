"""Web routes serving server-rendered HTML pages."""

from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.domain.enums import JobStage, JobStatus
from app.services.job_service import JobService
from app.storage.base import ArtifactStore

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STAGE_LABELS: dict[str, str] = {
    "planning": "1. Lập kế hoạch bài học",
    "validating_plan": "2. Kiểm tra cấu trúc bài học",
    "audio": "3. Tạo lời thuyết minh",
    "rendering": "4. Xây dựng hình minh họa",
    "assembling": "5. Ghép video",
    "validating_output": "6. Kiểm tra video cuối",
}

STAGE_DESCRIPTIONS: dict[str, str] = {
    "planning": "Đang sắp xếp các ý chính thành một bài học ngắn.",
    "validating_plan": "Đang kiểm tra mạch giải thích trước khi tiếp tục.",
    "audio": "Đang tạo lời thuyết minh cho từng phần.",
    "rendering": "Đang biến các ý chính thành hình ảnh dễ theo dõi.",
    "assembling": "Đang ghép lời thuyết minh và hình ảnh thành video.",
    "validating_output": "Đang xem lại video trước khi hoàn tất.",
}

STATUS_LABELS: dict[str, str] = {
    "queued": "Đang chờ",
    "running": "Đang chuẩn bị",
    "succeeded": "Hoàn tất",
    "failed": "Chưa hoàn tất",
}

STATUS_BADGES: dict[str, str] = {
    "queued": "Đang chờ ○",
    "running": "Đang chuẩn bị ●",
    "succeeded": "Hoàn tất ✓",
    "failed": "Chưa hoàn tất !",
}


def format_stage(val: Any) -> str:
    """Map raw JobStage enum to human Vietnamese text."""
    if not val:
        return "Khởi động"
    key = val.value.lower() if hasattr(val, "value") else str(val).lower()
    return STAGE_LABELS.get(key, "Đang xử lý")


def format_stage_desc(val: Any) -> str:
    """Map raw JobStage enum to natural progress description."""
    if not val:
        return "Đang chuẩn bị khởi động bài học."
    key = val.value.lower() if hasattr(val, "value") else str(val).lower()
    return STAGE_DESCRIPTIONS.get(key, "Đang xử lý nội dung bài học.")


def format_status(val: Any) -> str:
    """Map raw JobStatus enum to human Vietnamese text."""
    if not val:
        return ""
    key = val.value.lower() if hasattr(val, "value") else str(val).lower()
    return STATUS_LABELS.get(key, str(val))


def format_status_badge(val: Any) -> str:
    """Map raw JobStatus enum to status label with symbol."""
    if not val:
        return ""
    key = val.value.lower() if hasattr(val, "value") else str(val).lower()
    return STATUS_BADGES.get(key, str(val))


# Register custom filters
templates.env.filters["stage_label"] = format_stage
templates.env.filters["stage_desc"] = format_stage_desc
templates.env.filters["status_label"] = format_status
templates.env.filters["status_badge"] = format_status_badge
templates.env.globals["format_stage"] = format_stage
templates.env.globals["format_status"] = format_status
templates.env.globals["format_status_badge"] = format_status_badge

router = APIRouter(tags=["web"])


def get_job_service(request: Request) -> JobService:
    """Retrieve JobService instance from app state."""
    return request.app.state.job_service


def get_artifact_store(request: Request) -> ArtifactStore:
    """Retrieve ArtifactStore instance from app state."""
    return request.app.state.artifact_store


def get_pipeline_mode(request: Request) -> str:
    """Retrieve current pipeline mode from settings."""
    settings = getattr(request.app.state, "settings", None)
    if settings and hasattr(settings, "pipeline_mode"):
        return settings.pipeline_mode.lower().strip()
    return "real"


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    job_service: JobService = Depends(get_job_service),
) -> HTMLResponse:
    """Landing dashboard with immediate learning input, sample chips, and recent lessons."""
    recent_jobs = job_service.list_jobs(limit=5)
    pipeline_mode = get_pipeline_mode(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "recent_jobs": recent_jobs,
            "pipeline_mode": pipeline_mode,
            "active_nav": "home",
        },
    )


@router.get("/create", response_class=HTMLResponse)
def create_page(
    request: Request,
    topic: str = Query(default=""),
) -> HTMLResponse:
    """Create learning video form with audience, language, and duration options."""
    pipeline_mode = get_pipeline_mode(request)
    return templates.TemplateResponse(
        request=request,
        name="create.html",
        context={
            "prefill_topic": topic,
            "pipeline_mode": pipeline_mode,
            "active_nav": "create",
        },
    )


@router.get("/library", response_class=HTMLResponse)
def library_page(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    job_service: JobService = Depends(get_job_service),
) -> HTMLResponse:
    """Library showing historical generation jobs with clean status indicators."""
    filter_enum = None
    if status_filter:
        try:
            filter_enum = JobStatus(status_filter)
        except ValueError:
            pass

    jobs = job_service.list_jobs(limit=50, status=filter_enum)
    pipeline_mode = get_pipeline_mode(request)
    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context={
            "jobs": jobs,
            "current_filter": status_filter or "all",
            "pipeline_mode": pipeline_mode,
            "active_nav": "library",
        },
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail_page(
    job_id: str,
    request: Request,
    job_service: JobService = Depends(get_job_service),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> HTMLResponse:
    """Job detail page serving processing state, final video player, or failed explanation."""
    job = job_service.get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error_code": 404,
                "error_title": "Không tìm thấy bài học",
                "error_message": f"Không tìm thấy bài học nào với mã '{job_id}'.",
                "active_nav": "jobs",
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    pipeline_mode = get_pipeline_mode(request)

    # Verify if published final video artifact actually exists on disk
    has_video = False
    video_url = None
    actual_duration = None

    if job.status == JobStatus.SUCCEEDED:
        final_path = artifact_store.get_final_path(job.id)
        if final_path is not None and final_path.exists():
            has_video = True
            video_url = f"/api/jobs/{job.id}/video"
        if job.artifact_metadata and isinstance(job.artifact_metadata, dict):
            sec = job.artifact_metadata.get("duration_seconds")
            if sec and isinstance(sec, (int, float)):
                actual_duration = round(sec)

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={
            "job": job,
            "has_video": has_video,
            "video_url": video_url,
            "actual_duration": actual_duration,
            "pipeline_mode": pipeline_mode,
            "active_nav": "jobs",
        },
    )
