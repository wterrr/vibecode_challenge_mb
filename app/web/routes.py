"""Web routes serving server-rendered HTML pages."""

from pathlib import Path
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.job_service import JobService

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"])


def get_job_service(request: Request) -> JobService:
    """Retrieve JobService instance from app state."""
    return request.app.state.job_service


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    job_service: JobService = Depends(get_job_service),
) -> HTMLResponse:
    """Landing dashboard with value proposition, prompt chips, and recent jobs."""
    recent_jobs = job_service.list_jobs(limit=3)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"recent_jobs": recent_jobs},
    )


@router.get("/create", response_class=HTMLResponse)
def create_page(
    request: Request,
    topic: str = Query(default=""),
) -> HTMLResponse:
    """Create learning video form."""
    return templates.TemplateResponse(
        request=request,
        name="create.html",
        context={"prefill_topic": topic},
    )


@router.get("/library", response_class=HTMLResponse)
def library_page(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    job_service: JobService = Depends(get_job_service),
) -> HTMLResponse:
    """Library showing historical generation jobs."""
    from app.domain.enums import JobStatus

    filter_enum = None
    if status_filter:
        try:
            filter_enum = JobStatus(status_filter)
        except ValueError:
            pass

    jobs = job_service.list_jobs(limit=50, status=filter_enum)
    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context={"jobs": jobs, "current_filter": status_filter or "all"},
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail_page(
    job_id: str,
    request: Request,
    job_service: JobService = Depends(get_job_service),
) -> HTMLResponse:
    """Job detail tracking background generation or displaying final state."""
    job = job_service.get_job(job_id)
    if job is None:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={
                "error_code": 404,
                "error_title": "Không tìm thấy công việc",
                "error_message": f"Không tìm thấy công việc với mã '{job_id}'.",
            },
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={"job": job},
    )
