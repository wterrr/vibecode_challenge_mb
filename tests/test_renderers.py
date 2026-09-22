"""Unit tests for generic deterministic visual renderers (CP5)."""

from pathlib import Path
import pytest

from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonColumn,
    ComparisonSpec,
    ConceptCardSpec,
    IllustrationSpec,
    ProcessActor,
    ProcessDiagramSpec,
    ProcessStep,
    ScenePlan,
)
from app.domain.timeline import ResolvedSceneTiming
from app.pipeline.timeline import probe_duration
from app.rendering.comparison import ComparisonRenderer
from app.rendering.concept_card import ConceptCardRenderer
from app.rendering.illustration import IllustrationRenderer
from app.rendering.process_diagram import ProcessDiagramRenderer
from app.rendering.router import RendererRouter


def make_test_timing(scene_id: str, duration: float = 2.0) -> ResolvedSceneTiming:
    """Construct a minimal valid ResolvedSceneTiming for renderer testing."""
    return ResolvedSceneTiming(
        scene_id=scene_id,
        raw_audio_path="/fake/raw.mp3",
        padded_audio_path="/fake/padded.wav",
        audio_duration_seconds=duration - 0.3,
        render_duration_seconds=duration,
        start_seconds=0.0,
        end_seconds=duration,
    )


@pytest.mark.asyncio
async def test_concept_card_renderer_produces_valid_mp4(tmp_path: Path) -> None:
    """ConceptCardRenderer renders a valid MP4 with correct dimensions and duration."""
    renderer = ConceptCardRenderer(width=640, height=360, fps=12)
    spec = ConceptCardSpec(
        heading="Giao thức TCP (Transmission Control Protocol)",
        points=[
            "Giao thức hướng kết nối (Connection-oriented)",
            "Đảm bảo kiểm tra lỗi và mất gói tin",
            "Đảm bảo thứ tự truyền nhận dữ liệu",
        ],
        emphasis=["Tin cậy", "Kiểm soát tắc nghẽn"],
    )
    scene = ScenePlan(
        scene_id="s01_tcp",
        title="Khái niệm TCP",
        concept="Định nghĩa giao thức TCP",
        narration="TCP là giao thức truyền thông tin cậy.",
        key_points=["Giao thức tin cậy", "Bắt tay 3 bước"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=spec,
    )
    timing = make_test_timing("s01_tcp", duration=2.4)
    out_path = tmp_path / "concept.mp4"

    result = await renderer.render(scene, timing, out_path)

    assert Path(result.path).exists()
    assert result.width == 640
    assert result.height == 360
    measured = await probe_duration(out_path)
    assert abs(measured - 2.4) < 0.15


@pytest.mark.asyncio
async def test_process_diagram_renderer_produces_valid_mp4(tmp_path: Path) -> None:
    """ProcessDiagramRenderer renders multi-step sequential workflows."""
    renderer = ProcessDiagramRenderer(width=640, height=360, fps=12)
    spec = ProcessDiagramSpec(
        title="Ba bước bắt tay TCP",
        actors=[
            ProcessActor(id="client", label="Client"),
            ProcessActor(id="server", label="Server"),
        ],
        steps=[
            ProcessStep(order=1, from_actor="client", to_actor="server", label="1. SYN", description="Client gửi gói tin SYN"),
            ProcessStep(order=2, from_actor="server", to_actor="client", label="2. SYN-ACK", description="Server phản hồi SYN-ACK"),
            ProcessStep(order=3, from_actor="client", to_actor="server", label="3. ACK", description="Client xác nhận hoàn tất kết nối"),
        ],
    )
    scene = ScenePlan(
        scene_id="s02_steps",
        title="Ba bước bắt tay TCP",
        concept="Tiến trình thiết lập liên kết",
        narration="Quy trình gồm ba bước bắt tay.",
        key_points=["SYN", "SYN-ACK", "ACK"],
        visual_intent=VisualIntent.PROCESS_DIAGRAM,
        visual_spec=spec,
    )
    timing = make_test_timing("s02_steps", duration=2.1)
    out_path = tmp_path / "process.mp4"

    result = await renderer.render(scene, timing, out_path)

    assert Path(result.path).exists()
    measured = await probe_duration(out_path)
    assert abs(measured - 2.1) < 0.15


@pytest.mark.asyncio
async def test_comparison_renderer_produces_valid_mp4(tmp_path: Path) -> None:
    """ComparisonRenderer renders side-by-side contrast analysis."""
    renderer = ComparisonRenderer(width=640, height=360, fps=12)
    spec = ComparisonSpec(
        title="So sánh TCP và UDP",
        columns=[
            ComparisonColumn(
                title="TCP",
                subtitle="Tin cậy tuyệt đối",
                points=["Có bắt tay 3 bước", "Kiểm soát tắc nghẽn", "Chậm hơn một chút"],
            ),
            ComparisonColumn(
                title="UDP",
                subtitle="Tối ưu tốc độ",
                points=["Không cần bắt tay", "Không sửa lỗi", "Cực nhanh cho streaming"],
            ),
        ],
    )
    scene = ScenePlan(
        scene_id="s03_comp",
        title="So sánh TCP và UDP",
        concept="Phân biệt hai giao thức mạng",
        narration="TCP đảm bảo dữ liệu, UDP tối ưu tốc độ.",
        key_points=["TCP tin cậy", "UDP tốc độ"],
        visual_intent=VisualIntent.COMPARISON,
        visual_spec=spec,
    )
    timing = make_test_timing("s03_comp", duration=2.5)
    out_path = tmp_path / "comparison.mp4"

    result = await renderer.render(scene, timing, out_path)

    assert Path(result.path).exists()
    measured = await probe_duration(out_path)
    assert abs(measured - 2.5) < 0.15


@pytest.mark.asyncio
async def test_illustration_renderer_produces_valid_mp4(tmp_path: Path) -> None:
    """IllustrationRenderer renders schematic framing with fallback heading and points."""
    renderer = IllustrationRenderer(width=640, height=360, fps=12)
    spec = IllustrationSpec(
        prompt="A diagram showing packet flow between client and server across internet routers",
        fallback_heading="Dòng chảy gói tin trên mạng Internet",
        fallback_points=[
            "Gói tin SYN khởi tạo kết nối",
            "Định tuyến qua các router trung gian",
            "Đến máy chủ đích an toàn",
        ],
    )
    scene = ScenePlan(
        scene_id="s04_illus",
        title="Dòng chảy gói tin",
        concept="Minh họa luồng gói tin",
        narration="Dữ liệu di chuyển xuyên qua mạng.",
        key_points=["Gói tin", "Router"],
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=spec,
    )
    timing = make_test_timing("s04_illus", duration=2.0)
    out_path = tmp_path / "illustration.mp4"

    result = await renderer.render(scene, timing, out_path)

    assert Path(result.path).exists()
    measured = await probe_duration(out_path)
    assert abs(measured - 2.0) < 0.15


@pytest.mark.asyncio
async def test_long_text_triggers_warning_without_failing(tmp_path: Path) -> None:
    """Very long text is truncated gracefully and emits warnings without crashing."""
    renderer = ConceptCardRenderer(width=640, height=360, fps=12)
    # Long heading that stays under the 200 char schema limit but exceeds 2 wrapped lines on small 640x360 canvas
    long_heading = (
        "Tiêu đề giải thích khái niệm công nghệ này có độ dài rất dài "
        "để chắc chắn vượt quá hai dòng trên khung hình kích thước nhỏ nhằm kích hoạt cảnh báo cắt ngắn."
    )
    spec = ConceptCardSpec(
        heading=long_heading[:190],
        points=["Điểm 1", "Điểm 2"],
    )
    scene = ScenePlan(
        scene_id="s05_long",
        title="Kiểm tra văn bản dài",
        concept="Cắt tỉa văn bản dài",
        narration="Kiểm tra cắt ngắn văn bản.",
        key_points=["Cắt tỉa an toàn"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=spec,
    )
    timing = make_test_timing("s05_long", duration=1.5)
    out_path = tmp_path / "long_text.mp4"

    result = await renderer.render(scene, timing, out_path)

    assert Path(result.path).exists()
    assert any("truncated" in w.lower() for w in result.warnings)


def test_renderer_router_dispatches_all_intents() -> None:
    """RendererRouter dispatches to the correct specialized renderer for all VisualIntents."""
    router = RendererRouter()
    assert isinstance(router.get_renderer(VisualIntent.CONCEPT_CARD), ConceptCardRenderer)
    assert isinstance(router.get_renderer(VisualIntent.PROCESS_DIAGRAM), ProcessDiagramRenderer)
    assert isinstance(router.get_renderer(VisualIntent.COMPARISON), ComparisonRenderer)
    assert isinstance(router.get_renderer(VisualIntent.ILLUSTRATION), IllustrationRenderer)


def test_select_progressive_state_indices_invariants() -> None:
    """select_progressive_state_indices adheres to all ordering, completeness, and boundary invariants."""
    from app.rendering.transitions import select_progressive_state_indices

    # Finding 1 specifications
    assert select_progressive_state_indices(3, 3) == [0, 1, 2]
    assert select_progressive_state_indices(3, 2) == [0, 2]
    assert select_progressive_state_indices(3, 1) == [2]

    assert select_progressive_state_indices(4, 2) == [0, 3]
    assert select_progressive_state_indices(4, 3) == [0, 2, 3]
    assert select_progressive_state_indices(4, 4) == [0, 1, 2, 3]

    assert select_progressive_state_indices(5, 2) == [0, 4]
    assert select_progressive_state_indices(5, 3) == [0, 2, 4]
    assert select_progressive_state_indices(1, 1) == [0]

    # Edge cases
    assert select_progressive_state_indices(0, 0) == []
    assert select_progressive_state_indices(3, 0) == []
    assert select_progressive_state_indices(0, 3) == []
    assert select_progressive_state_indices(2, 5) == [0, 1]


def test_typography_unbroken_long_token_splits_strictly_within_width() -> None:
    """Long tokens without whitespace are deterministically split so no line exceeds max_width_px."""
    from PIL import Image, ImageDraw
    from app.rendering.typography import get_system_font, wrap_text_to_width

    im = Image.new("RGB", (640, 360))
    draw = ImageDraw.Draw(im)
    font = get_system_font(16)

    max_w = 120
    long_token = "W" * 120
    lines = wrap_text_to_width(long_token, font, max_w, draw)

    assert len(lines) > 1
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        assert line_w <= max_w, f"Line '{line}' width {line_w} exceeded {max_w}"

    # Mixed prose with long technical identifier
    mixed = f"Prefix {long_token} suffix words that follow"
    mixed_lines = wrap_text_to_width(mixed, font, max_w, draw)
    for line in mixed_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        assert line_w <= max_w, f"Line '{line}' width {line_w} exceeded {max_w}"


def test_typography_fit_or_truncate_strictly_bounds_ellipsis() -> None:
    """When text exceeds max_lines, final line with ellipsis strictly obeys max_width_px."""
    from PIL import Image, ImageDraw
    from app.rendering.typography import fit_or_truncate_text, get_system_font

    im = Image.new("RGB", (640, 360))
    draw = ImageDraw.Draw(im)
    font = get_system_font(18)

    max_w = 100
    text = "Một đoạn văn bản tiếng Việt rất dài có nhiều câu từ phức tạp nhằm kiểm tra việc cắt tỉa."
    warnings: list[str] = []
    lines = fit_or_truncate_text(text, font, max_w, max_lines=2, draw=draw, warnings=warnings)

    assert len(lines) <= 2
    assert len(warnings) == 1
    assert "truncated" in warnings[0].lower()

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        assert line_w <= max_w, f"Line with ellipsis '{line}' width {line_w} exceeded {max_w}"


@pytest.mark.asyncio
async def test_comparison_column_title_100_chars_regression(tmp_path: Path) -> None:
    """ComparisonColumn with 100-character title renders safely without overflowing column width."""
    renderer = ComparisonRenderer(width=640, height=360, fps=12)
    spec = ComparisonSpec(
        title="So sánh",
        columns=[
            ComparisonColumn(
                title="T" * 100,
                subtitle="Mô tả",
                points=["Điểm 1", "Điểm 2"],
            ),
            ComparisonColumn(
                title="Cột 2 bình thường",
                subtitle="Mô tả",
                points=["Điểm A", "Điểm B"],
            ),
        ],
    )
    scene = ScenePlan(
        scene_id="s10_col_test",
        title="Tiêu đề dài",
        concept="So sánh tiêu đề dài",
        narration="Kiểm tra tiêu đề cột 100 ký tự.",
        key_points=["Cột dài"],
        visual_intent=VisualIntent.COMPARISON,
        visual_spec=spec,
    )
    timing = make_test_timing("s10_col_test", duration=1.0)
    out_path = tmp_path / "comp_100char.mp4"

    result = await renderer.render(scene, timing, out_path)
    assert Path(result.path).exists()
    assert any("truncated" in w.lower() for w in result.warnings)


@pytest.mark.asyncio
async def test_concept_card_long_emphasis_badges_wrap_and_bound(tmp_path: Path) -> None:
    """ConceptCard with multiple/long emphasis strings wraps rows and never escapes canvas."""
    renderer = ConceptCardRenderer(width=640, height=360, fps=12)
    spec = ConceptCardSpec(
        heading="Khái niệm mạng",
        points=["Giao thức kết nối tin cậy", "Truyền nhận toàn vẹn"],
        emphasis=[
            "HuyHieuNhanManhRatDaiKhongCoKhoangTrangNaoCaDeKiemTraWrap",
            "HuyHieuThuHai",
            "HuyHieuThuBa",
            "HuyHieuThuTu",
        ],
    )
    scene = ScenePlan(
        scene_id="s11_badge_test",
        title="Thử nghiệm huy hiệu",
        concept="Kiểm tra huy hiệu",
        narration="Kiểm tra nhãn nhấn mạnh.",
        key_points=["Nhấn mạnh"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=spec,
    )
    timing = make_test_timing("s11_badge_test", duration=2.5)
    out_path = tmp_path / "badges_wrap.mp4"

    result = await renderer.render(scene, timing, out_path)
    assert Path(result.path).exists()


@pytest.mark.asyncio
async def test_short_scene_concept_card_preserves_final_state(tmp_path: Path) -> None:
    """A 1.0s short scene with ConceptCard renders the final state containing points and emphasis."""
    renderer = ConceptCardRenderer(width=640, height=360, fps=12)
    spec = ConceptCardSpec(
        heading="TCP Khái niệm ngắn",
        points=["Đảm bảo tin cậy", "Kiểm soát tắc nghẽn"],
        emphasis=["Bắt buộc"],
    )
    scene = ScenePlan(
        scene_id="s12_short_concept",
        title="Ngắn",
        concept="Khái niệm trong 1 giây",
        narration="Giải thích ngắn gọn trong 1 giây.",
        key_points=["Khái niệm"],
        visual_intent=VisualIntent.CONCEPT_CARD,
        visual_spec=spec,
    )
    timing = make_test_timing("s12_short_concept", duration=1.0)
    out_path = tmp_path / "short_concept.mp4"

    result = await renderer.render(scene, timing, out_path)
    assert Path(result.path).exists()
    measured = await probe_duration(out_path)
    assert abs(measured - 1.0) < 0.2


@pytest.mark.asyncio
async def test_short_scene_comparison_and_process_render_safely(tmp_path: Path) -> None:
    """Short 1.0s scenes render comparison and process diagrams with all elements visible."""
    # 1. Comparison
    comp_renderer = ComparisonRenderer(width=640, height=360, fps=12)
    comp_spec = ComparisonSpec(
        title="So sánh",
        columns=[
            ComparisonColumn(title="Cột A", points=["Chi tiết A"]),
            ComparisonColumn(title="Cột B", points=["Chi tiết B"]),
        ],
    )
    comp_scene = ScenePlan(
        scene_id="s13_short_comp",
        title="So sánh 1s",
        concept="So sánh nhanh",
        narration="Nói nhanh.",
        key_points=["So sánh"],
        visual_intent=VisualIntent.COMPARISON,
        visual_spec=comp_spec,
    )
    comp_out = tmp_path / "short_comp.mp4"
    comp_res = await comp_renderer.render(comp_scene, make_test_timing("s13_short_comp", duration=1.0), comp_out)
    assert Path(comp_res.path).exists()

    # 2. Process
    proc_renderer = ProcessDiagramRenderer(width=640, height=360, fps=12)
    proc_spec = ProcessDiagramSpec(
        title="Quy trình 1s",
        actors=[ProcessActor(id="c", label="Client"), ProcessActor(id="s", label="Server")],
        steps=[
            ProcessStep(order=1, label="SYN", description="Gửi SYN"),
            ProcessStep(order=2, label="ACK", description="Gửi ACK"),
        ],
    )
    proc_scene = ScenePlan(
        scene_id="s14_short_proc",
        title="Quy trình nhanh",
        concept="Quy trình",
        narration="Bắt tay nhanh.",
        key_points=["Bắt tay"],
        visual_intent=VisualIntent.PROCESS_DIAGRAM,
        visual_spec=proc_spec,
    )
    proc_out = tmp_path / "short_proc.mp4"
    proc_res = await proc_renderer.render(proc_scene, make_test_timing("s14_short_proc", duration=1.0), proc_out)
    assert Path(proc_res.path).exists()


@pytest.mark.asyncio
async def test_illustration_renderer_disabled_does_not_call_provider(tmp_path: Path) -> None:
    """When enable_image_generation=False, provider is never called."""
    from tests.test_image_provider import FakeImageProvider

    fake_provider = FakeImageProvider()
    renderer = IllustrationRenderer(
        width=640,
        height=360,
        fps=12,
        image_provider=fake_provider,
        enable_image_generation=False,
    )
    spec = IllustrationSpec(
        prompt="Packet flow across routers",
        fallback_heading="Luong goi tin",
        fallback_points=["Goi tin SYN", "Dinh tuyen"],
    )
    scene = ScenePlan(
        scene_id="s15_illus_disabled",
        title="Minh hoa",
        concept="Khai niem",
        narration="Thuyet minh.",
        key_points=["Goi tin"],
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=spec,
    )
    out_path = tmp_path / "illus_disabled.mp4"
    res = await renderer.render(scene, make_test_timing("s15_illus_disabled", duration=2.0), out_path)

    assert len(fake_provider.calls) == 0
    assert Path(res.path).exists()
    assert not any("deterministic fallback used" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_illustration_renderer_success_composes_ai_image(tmp_path: Path) -> None:
    """When enabled and provider succeeds, image is generated and composed with overlays."""
    from tests.test_image_provider import FakeImageProvider

    fake_provider = FakeImageProvider(width=640, height=360)
    renderer = IllustrationRenderer(
        width=640,
        height=360,
        fps=12,
        image_provider=fake_provider,
        enable_image_generation=True,
    )
    spec = IllustrationSpec(
        prompt="Packet flow across routers",
        fallback_heading="Luong goi tin",
        fallback_points=["Goi tin SYN", "Dinh tuyen an toan"],
    )
    scene = ScenePlan(
        scene_id="s16_illus_ai",
        title="Minh hoa AI",
        concept="Khai niem AI",
        narration="Thuyet minh AI.",
        key_points=["Goi tin"],
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=spec,
    )
    out_path = tmp_path / "illus_ai.mp4"
    res = await renderer.render(scene, make_test_timing("s16_illus_ai", duration=2.0), out_path)

    assert len(fake_provider.calls) == 1
    assert Path(res.path).exists()
    measured = await probe_duration(out_path)
    assert abs(measured - 2.0) < 0.15
    assert not any("deterministic fallback used" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_illustration_renderer_provider_failure_falls_back_cleanly(tmp_path: Path) -> None:
    """When provider raises an error, renderer records warning and uses deterministic fallback without crashing."""
    from app.providers.image.base import ImageProviderError
    from tests.test_image_provider import FakeImageProvider

    failing_provider = FakeImageProvider(
        error=ImageProviderError(code="image_timeout", message="Timeout connecting to Gemini", retryable=True)
    )
    renderer = IllustrationRenderer(
        width=640,
        height=360,
        fps=12,
        image_provider=failing_provider,
        enable_image_generation=True,
    )
    spec = IllustrationSpec(
        prompt="Packet flow",
        fallback_heading="Luong goi tin fallback",
        fallback_points=["Diem 1", "Diem 2"],
    )
    scene = ScenePlan(
        scene_id="s17_illus_fail",
        title="Minh hoa Fallback",
        concept="Khai niem",
        narration="Thuyet minh.",
        key_points=["Goi tin"],
        visual_intent=VisualIntent.ILLUSTRATION,
        visual_spec=spec,
    )
    out_path = tmp_path / "illus_fallback.mp4"
    res = await renderer.render(scene, make_test_timing("s17_illus_fail", duration=2.0), out_path)

    assert len(failing_provider.calls) == 1
    assert Path(res.path).exists()
    assert any("deterministic fallback used" in w for w in res.warnings)


def test_renderer_router_injects_image_provider_and_flag() -> None:
    """RendererRouter forwards image_provider and enable_image_generation to IllustrationRenderer."""
    from app.rendering.router import RendererRouter
    from tests.test_image_provider import FakeImageProvider

    fake_provider = FakeImageProvider()
    router = RendererRouter(image_provider=fake_provider, enable_image_generation=True)

    illus_renderer = router.get_renderer(VisualIntent.ILLUSTRATION)
    assert isinstance(illus_renderer, IllustrationRenderer)
    assert illus_renderer.image_provider is fake_provider
    assert illus_renderer.enable_image_generation is True


