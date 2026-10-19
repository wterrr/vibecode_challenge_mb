"""Opt-in React landing entrypoint; legacy web and V2 job routes stay untouched."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["v3-97-react-landing"])
_INDEX = Path(__file__).resolve().parent.parent / "static" / "landing" / "index.html"


@router.get("/", include_in_schema=False)
def react_home() -> FileResponse:
    if not _INDEX.is_file() or _INDEX.is_symlink():
        raise HTTPException(status_code=503, detail="React bundle missing; import uploaded FE ZIP and build")
    return FileResponse(_INDEX, media_type="text/html", headers={"Cache-Control": "no-cache"})
