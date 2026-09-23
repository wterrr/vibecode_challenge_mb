"""Tests for offline Demo mode planner and filename sanitization."""

import pytest
from app.api.routes import sanitize_download_filename
from app.demo.planner import DemoPlanner
from app.domain.lesson import LearningRequest
from app.providers.llm.base import PlannerProviderError


@pytest.mark.asyncio
async def test_demo_planner_supported_topics() -> None:
    planner = DemoPlanner()

    # 1. TCP
    req_tcp = LearningRequest(topic="How does the TCP three-way handshake work?", audience="Developer", language="vi")
    plan_tcp = await planner.create_plan(req_tcp)
    assert len(plan_tcp.scenes) == 3
    assert "TCP" in plan_tcp.title

    # 2. Photosynthesis
    req_photo = LearningRequest(topic="Quang hợp", audience="Student", language="vi")
    plan_photo = await planner.create_plan(req_photo)
    assert len(plan_photo.scenes) == 3
    assert "quang hợp" in plan_photo.title.lower()

    # 3. RAM vs SSD
    req_ram = LearningRequest(topic="RAM vs SSD for a beginner.", audience="Beginner", language="vi")
    plan_ram = await planner.create_plan(req_ram)
    assert len(plan_ram.scenes) == 3
    assert "RAM" in plan_ram.title


@pytest.mark.asyncio
async def test_demo_planner_unsupported_topic_fails() -> None:
    planner = DemoPlanner()
    req = LearningRequest(topic="Quantum computing entanglement", audience="Expert", language="en")

    with pytest.raises(PlannerProviderError) as exc_info:
        await planner.create_plan(req)

    err = exc_info.value
    assert err.code == "demo_topic_not_available"
    assert err.retryable is False
    assert "not available in offline demo mode" in err.message


@pytest.mark.asyncio
async def test_demo_planner_ram_vs_ssd_documented_fixture() -> None:
    """DEMO known topic RAM vs SSD returns documented validated fixture."""
    from app.demo.lesson_plans import DEMO_RAM_SSD_PLAN
    planner = DemoPlanner()
    req = LearningRequest(topic="RAM vs SSD", audience="General", language="vi")
    plan = await planner.create_plan(req)
    assert plan.title == DEMO_RAM_SSD_PLAN.title
    assert len(plan.scenes) == len(DEMO_RAM_SSD_PLAN.scenes)
    assert plan.scenes[0].title == DEMO_RAM_SSD_PLAN.scenes[0].title


@pytest.mark.asyncio
async def test_demo_planner_quantum_chromodynamics_fails_strictly() -> None:
    """DEMO unsupported topic 'Explain quantum chromodynamics' must produce demo_topic_not_available."""
    planner = DemoPlanner()
    req = LearningRequest(topic="Explain quantum chromodynamics", audience="Undergrad", language="en")

    with pytest.raises(PlannerProviderError) as exc_info:
        await planner.create_plan(req)

    err = exc_info.value
    assert err.code == "demo_topic_not_available"
    assert err.retryable is False
    assert "not available in offline demo mode" in err.message


def test_sanitize_download_filename_edge_cases() -> None:
    # Traversal and invalid characters
    assert sanitize_download_filename("../../../etc/passwd") == "etc-passwd.mp4"
    assert sanitize_download_filename("my/cool:video*title?.mp4") == "my-cool-video-title.mp4"
    assert sanitize_download_filename('quote "and" newline\n\r\t') == "quote-and-newline.mp4"

    # Blank fallback
    assert sanitize_download_filename("") == "learnflow-video.mp4"
    assert sanitize_download_filename("   ") == "learnflow-video.mp4"
    assert sanitize_download_filename(None) == "learnflow-video.mp4"

    # Vietnamese characters preserved
    vn_title = "Cơ chế bắt tay 3 bước TCP"
    sanitized = sanitize_download_filename(vn_title)
    assert "Cơ-chế-bắt-tay-3-bước-TCP.mp4" in sanitized

    # Max length truncation
    long_title = "a" * 150
    truncated = sanitize_download_filename(long_title, max_length=50)
    assert len(truncated) <= 54  # 50 + len('.mp4')
    assert truncated.endswith(".mp4")
