"""Comprehensive tests for CP9 UI/UX design, templates, stages, and security."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import JobStage, JobStatus
from app.domain.errors import JobError
from app.domain.jobs import Job
from app.main import create_app
from app.repositories.sqlite import SqliteJobRepository
from app.storage.local import LocalArtifactStore
from tests.conftest import make_test_job


@pytest.fixture
def cp9_app(tmp_path: Path):
    """Create test application instance with clean isolated SQLite and artifact store."""
    db_file = tmp_path / "cp9_test.db"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        db_path=str(db_file),
        artifacts_dir=str(artifacts_dir),
        pipeline_mode="demo",
    )
    repo = SqliteJobRepository(str(db_file))
    store = LocalArtifactStore(str(artifacts_dir))
    app = create_app(
        settings=settings,
        repository=repo,
        artifact_store=store,
    )
    return app, repo, store


def test_landing_page_ui(cp9_app):
    """GET / renders human-centric learning landing with prompt entry and sample chips."""
    app, repo, _ = cp9_app
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        html = res.text

        # Brand & Headline
        assert "LearnFlow" in html
        assert "Bạn muốn hiểu điều gì hôm nay?" in html
        assert "Nhập một chủ đề bạn đang muốn hiểu" in html

        # Topic entry form
        assert 'name="topic"' in html
        assert "Tạo bài học" in html

        # Sample topic chips
        assert "TCP three-way handshake" in html
        assert "Quá trình quang hợp" in html
        assert "RAM và SSD khác nhau thế nào?" in html

        # Must not contain banned AI clichés
        assert "SYS //" not in html
        assert "LAB //" not in html
        assert "ARCHIVE" not in html
        assert "AI v2.4" not in html


def test_create_page_demo_mode_honesty(cp9_app):
    """GET /create displays honest demo mode notice and supported topics when in demo mode."""
    app, repo, _ = cp9_app
    with TestClient(app) as client:
        res = client.get("/create")
        assert res.status_code == 200
        html = res.text

        assert "Tạo một bài học mới" in html
        assert "Chế độ demo" in html
        assert "Bản demo hiện hỗ trợ một số chủ đề mẫu" in html
        assert 'data-topic="How does the TCP three-way handshake work?"' in html

        # Settings
        assert 'name="audience"' in html
        assert 'name="language"' in html
        assert 'name="target_duration_seconds"' in html


def test_create_page_real_mode_no_demo_badge(tmp_path: Path):
    """GET /create does not show demo mode badge when pipeline_mode is real."""
    db_file = tmp_path / "real_test.db"
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        db_path=str(db_file),
        artifacts_dir=str(artifacts_dir),
        pipeline_mode="real",
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        res = client.get("/create")
        assert res.status_code == 200
        html = res.text
        assert "Chế độ demo" not in html


def test_library_page_vietnamese_status_badges(cp9_app):
    """GET /library maps all raw statuses to user-friendly text + symbols."""
    app, repo, _ = cp9_app
    j1 = make_test_job("job-q", "Topic Queued", status=JobStatus.QUEUED, progress_percent=0)
    j2 = make_test_job("job-r", "Topic Running", status=JobStatus.RUNNING, progress_percent=40)
    j2.stage = JobStage.AUDIO
    j3 = make_test_job("job-s", "Topic Succeeded", status=JobStatus.SUCCEEDED, progress_percent=100)
    j4 = make_test_job("job-f", "Topic Failed", status=JobStatus.FAILED, progress_percent=20)

    for j in [j1, j2, j3, j4]:
        repo.create(j)

    with TestClient(app) as client:
        res = client.get("/library")
        assert res.status_code == 200
        html = res.text

        # User-friendly Vietnamese statuses with symbols
        assert "Đang chờ ○" in html
        assert "Đang chuẩn bị ●" in html
        assert "Hoàn tất ✓" in html
        assert "Chưa hoàn tất !" in html

        # Delete dialog component present
        assert 'id="delete-dialog"' in html


def test_processing_page_stages_and_no_video(cp9_app):
    """Running/queued job renders 6-step sequence, exact progress, and NO video player."""
    app, repo, _ = cp9_app
    job = make_test_job(
        "job-proc-1",
        "Exploring Neural Networks",
        status=JobStatus.RUNNING,
        progress_percent=60,
    )
    job.stage = JobStage.RENDERING
    repo.create(job)

    with TestClient(app) as client:
        res = client.get("/jobs/job-proc-1")
        assert res.status_code == 200
        html = res.text

        # Header info
        assert "Đang chuẩn bị bài học" in html
        assert "Exploring Neural Networks" in html
        assert "60%" in html

        # All 6 stages represented in vertical sequence
        assert "Lập kế hoạch bài học" in html
        assert "Kiểm tra cấu trúc bài học" in html
        assert "Tạo lời thuyết minh" in html
        assert "Xây dựng hình minh họa" in html
        assert "Ghép video" in html
        assert "Kiểm tra video cuối" in html

        # No raw JobStage string rendered as human text
        assert "RENDERING" not in html
        assert "JobStage" not in html

        # Absolute Invariant: No video player during processing!
        assert "<video" not in html


def test_succeeded_job_with_real_video_artifact(cp9_app):
    """Succeeded job with real final.mp4 renders video player, download CTA, and edit controls."""
    app, repo, store = cp9_app
    job = make_test_job(
        "job-success-1",
        "Understanding Distributed Systems",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    job.artifact_path = "final.mp4"
    job.artifact_metadata = {"duration_seconds": 79.0}
    repo.create(job)

    # Publish dummy final.mp4 in artifact store
    dest_dir = store.get_job_dir("job-success-1")
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "final.mp4").write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 200)

    with TestClient(app) as client:
        res = client.get("/jobs/job-success-1")
        assert res.status_code == 200
        html = res.text

        assert "Bài học của bạn đã sẵn sàng" in html
        assert "Understanding Distributed Systems" in html

        # Video player present with correct URL
        assert '<video id="player"' in html
        assert '<source src="/api/jobs/job-success-1/video" type="video/mp4"' in html

        # Download CTA
        assert 'href="/api/jobs/job-success-1/video"' in html
        assert "Tải video" in html

        # Actual duration rendered
        assert "79 giây" in html

        # Rename & Delete actions
        assert "Đổi tên" in html
        assert 'id="btn-delete-job"' in html


def test_succeeded_job_without_video_artifact_rejects_player(cp9_app):
    """Succeeded job lacking final.mp4 on disk does NOT render fake video player."""
    app, repo, _ = cp9_app
    job = make_test_job(
        "job-no-video",
        "Ghost Job Missing Video",
        status=JobStatus.SUCCEEDED,
        progress_percent=100,
    )
    repo.create(job)

    with TestClient(app) as client:
        res = client.get("/jobs/job-no-video")
        assert res.status_code == 200
        html = res.text

        # Must NOT render <video> tag
        assert "<video" not in html
        assert "Video chưa thể tải lúc này" in html or "Chế độ phát triển" in html


def test_failed_job_safe_human_presentation(cp9_app):
    """Failed job renders calm explanation without raw exception traceback or technical codes."""
    app, repo, _ = cp9_app
    job = make_test_job(
        "job-fail-1",
        "Quantum Computing Concepts",
        status=JobStatus.FAILED,
        progress_percent=40,
    )
    job.error = JobError(
        code="tts_voice_timeout",
        message="TTS synthesis request timed out after 30 seconds",
        stage=JobStage.AUDIO,
    )
    repo.create(job)

    with TestClient(app) as client:
        res = client.get("/jobs/job-fail-1")
        assert res.status_code == 200
        html = res.text

        # Calm headline
        assert "Bài học này chưa được tạo xong" in html
        assert "LearnFlow gặp sự cố khi chuẩn bị bài học" in html

        # Human-mapped stage
        assert "Tạo lời thuyết minh" in html

        # Must NOT leak raw technical code or traceback
        assert "tts_voice_timeout" not in html
        assert "Traceback" not in html
        assert "<video" not in html

        # Helpful CTAs
        assert "Tạo bài học khác" in html
        assert "Quay lại thư viện" in html


def test_xss_protection_in_templates(cp9_app):
    """User-supplied topic or display_title is escaped and cannot execute script tags."""
    app, repo, _ = cp9_app
    malicious_topic = '<script>alert("xss")</script>'
    job = make_test_job(
        "job-xss",
        malicious_topic,
        status=JobStatus.QUEUED,
        progress_percent=0,
    )
    job.display_title = '<img src="x" onerror="alert(1)">'
    repo.create(job)

    with TestClient(app) as client:
        res = client.get("/jobs/job-xss")
        assert res.status_code == 200
        html = res.text

        # The literal tag must be escaped by Jinja autoescaping
        assert '<script>alert("xss")</script>' not in html
        assert "&lt;img" in html or "&lt;script" in html


def test_design_md_tokens_fidelity(cp9_app):
    """Verify DESIGN.md tokens: colors, typography, spacing, border-radius, and font links."""
    app, _, _ = cp9_app
    with TestClient(app) as client:
        # Check base.html font import
        res_home = client.get("/")
        assert res_home.status_code == 200
        assert "Be+Vietnam+Pro" in res_home.text
        assert "JetBrains+Mono" in res_home.text

        # Check CSS tokens in app.css
        res_css = client.get("/static/css/app.css")
        assert res_css.status_code == 200
        css = res_css.text

        # Color tokens from DESIGN.md
        assert "--canvas: #F8FAFC;" in css
        assert "--surface: #FFFFFF;" in css
        assert "--surface-muted: #F1F5F9;" in css
        assert "--border: #E2E8F0;" in css
        assert "--border-strong: #CBD5E1;" in css
        assert "--primary-text: #0F172A;" in css
        assert "--body-text: #334155;" in css
        assert "--muted-text: #64748B;" in css
        assert "--primary-action: #2563EB;" in css
        assert "--primary-hover: #1D4ED8;" in css
        assert "--primary-active: #1E40AF;" in css
        assert "--status-running: #2563EB;" in css
        assert "--status-running-bg: #EFF6FF;" in css
        assert "--status-succeeded: #059669;" in css
        assert "--status-succeeded-bg: #ECFDF5;" in css
        assert "--status-queued: #D97706;" in css
        assert "--status-queued-bg: #FFFBEB;" in css
        assert "--status-failed: #DC2626;" in css
        assert "--status-failed-bg: #FEF2F2;" in css

        # Typography tokens from DESIGN.md
        assert "'Be Vietnam Pro'" in css
        assert "'JetBrains Mono'" in css

        # Border-radius tokens from DESIGN.md
        assert "--rounded-sm: 0.25rem;" in css
        assert "--rounded: 0.5rem;" in css
        assert "--rounded-md: 0.75rem;" in css
        assert "--rounded-lg: 1rem;" in css
        assert "--rounded-xl: 1.5rem;" in css
        assert "--rounded-full: 9999px;" in css

        # Spacing tokens from DESIGN.md
        assert "--space-xs: 0.25rem;" in css
        assert "--space-sm: 0.5rem;" in css
        assert "--space-md: 1rem;" in css
        assert "--space-lg: 1.5rem;" in css
        assert "--space-xl: 2rem;" in css
        assert "--gutter: 1rem;" in css
        assert "--gutter-lg: 1.5rem;" in css

