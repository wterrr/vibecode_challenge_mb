"""Opt-in React landing entrypoint for LearnFlow FastAPI.

Mount only after the Vite production bundle is copied into app/static/landing.
The existing /api/jobs, /api/v3/ai and server-rendered /create routes remain unchanged.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["react-landing"])
_INDEX = Path(__file__).resolve().parent.parent / "static" / "landing" / "index.html"


@router.get("/", include_in_schema=False)
def react_home() -> FileResponse:
    if not _INDEX.is_file():
        raise HTTPException(status_code=503, detail="React landing not built; run frontend install script")
    return FileResponse(_INDEX, media_type="text/html", headers={"Cache-Control": "no-cache"})
