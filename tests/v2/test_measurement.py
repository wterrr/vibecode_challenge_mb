"""Comprehensive unit and acceptance tests for LearnFlow V2.1 intrinsic measurement."""

import json
import math
from pathlib import Path
from PIL import Image
import pytest
from pydantic import ValidationError

from learnflow_v2.core.errors import (
    MeasurementAssetNotFoundError,
    MeasurementFontNotFoundError,
    MeasurementInvalidAssetError,
    MeasurementInvalidInputError,
    MeasurementUnsupportedMathError,
    MeasurementUnsupportedNodeError,
)
from learnflow_v2.core.serialization import canonical_json
from learnflow_v2.layout.measurement import (
    AssetMeasurement,
    IconMeasurement,
    IntrinsicSize,
    MathMeasurement,
    MeasurementPolicy,
    TextMeasurement,
    WrapCandidate,
    measure_asset,
    measure_icon,
    measure_math,
    measure_node,
    measure_text,
    resolve_font_path,
)
from learnflow_v2.scenegraph.enums import NodeKind
from learnflow_v2.scenegraph.schema import SceneNode


@pytest.fixture
def sample_test_image(tmp_path: Path) -> Path:
    """Create a temporary valid PNG image for asset measurement testing."""
    img_path = tmp_path / "test_sample.png"
    img = Image.new("RGBA", (200, 100), color=(255, 0, 0, 255))
    img.save(img_path)
    return img_path


@pytest.fixture
def corrupt_test_image(tmp_path: Path) -> Path:
    """Create a corrupt image file with invalid binary header."""
    corrupt_path = tmp_path / "corrupt.png"
    corrupt_path.write_bytes(b"NOT_A_VALID_PNG_FILE_HEADER_DATA_12345")
    return corrupt_path


# ---------------------------------------------------------------------------
# Font Resolution & Stability Tests
# ---------------------------------------------------------------------------


def test_font_resolver_finds_system_font():
    font_path = resolve_font_path()
    assert font_path.is_file()
    assert font_path.suffix.lower() == ".ttf"


def test_font_resolver_rejects_missing_explicit_path():
    with pytest.raises(MeasurementFontNotFoundError) as exc_info:
        resolve_font_path("/nonexistent/path/to/MissingFont.ttf")
    assert exc_info.value.code == "MEASUREMENT_FONT_NOT_FOUND"


# ---------------------------------------------------------------------------
# Text Measurement Tests
# ---------------------------------------------------------------------------


def test_text_measurement_deterministic():
    text = "Deterministic Intrinsic Measurement V2.1"
    policy = MeasurementPolicy(preferred_font_size=24.0)

    m1 = measure_text(text, policy)
    m2 = measure_text(text, policy)

    assert m1.width == m2.width
    assert m1.height == m2.height
    assert m1.line_count == m2.line_count
    assert m1.minimum_readable_width == m2.minimum_readable_width
    assert m1.minimum_readable_height == m2.minimum_readable_height
    assert canonical_json(m1) == canonical_json(m2)


def test_vietnamese_measurement_preserves_diacritics():
    vi_text = "Giải thích quá trình quang hợp trong lục lạp của tế bào thực vật"
    policy = MeasurementPolicy(preferred_font_size=24.0)
    m = measure_text(vi_text, policy)

    assert m.content == vi_text
    assert m.width > 0.0
    assert m.height > 0.0
    # Ensure diacritics are not stripped or converted to ASCII
    assert "quang hợp" in m.content
    assert "quang hop" not in m.content
    assert m.minimum_readable_width > 0.0
    assert m.minimum_readable_height > 0.0


def test_font_size_monotonicity():
    text = "Comparative Scale Test"
    small = measure_text(text, MeasurementPolicy(preferred_font_size=16.0))
    medium = measure_text(text, MeasurementPolicy(preferred_font_size=24.0))
    large = measure_text(text, MeasurementPolicy(preferred_font_size=36.0))

    assert small.width < medium.width < large.width
    assert small.height <= medium.height <= large.height
    assert small.line_height < medium.line_height < large.line_height


def test_content_length_monotonicity():
    short_text = "Short text"
    long_text = "Short text followed by a significantly longer explanation that spans much wider"
    policy = MeasurementPolicy(preferred_font_size=24.0)

    m_short = measure_text(short_text, policy)
    m_long = measure_text(long_text, policy)

    assert m_short.width < m_long.width


def test_empty_or_whitespace_text_rejected():
    with pytest.raises(MeasurementInvalidInputError) as exc_1:
        measure_text("")
    assert exc_1.value.code == "MEASUREMENT_INVALID_INPUT"

    with pytest.raises(MeasurementInvalidInputError) as exc_2:
        measure_text("   \t  \n  ")
    assert exc_2.value.code == "MEASUREMENT_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Wrap Candidates Tests
# ---------------------------------------------------------------------------


def test_wrap_candidates_deterministic_and_preserve_tokens():
    text = "Backpropagation updates every parameter in the neural network"
    policy = MeasurementPolicy(
        preferred_font_size=24.0,
        candidate_max_widths=[200.0, 350.0, 500.0, 900.0],
    )
    m = measure_text(text, policy)

    assert len(m.wrap_candidates) == 4
    orig_tokens = text.split()

    for cand in m.wrap_candidates:
        cand_tokens = (" ".join(cand.lines)).split()
        assert cand_tokens == orig_tokens, f"Wrap candidate corrupted tokens: {cand.lines}"
        assert cand.width > 0.0
        assert cand.height > 0.0

    # At 200px width, text must have more lines than at 900px width
    narrow_cand = m.wrap_candidates[0]
    wide_cand = m.wrap_candidates[3]
    assert narrow_cand.line_count > wide_cand.line_count
    assert narrow_cand.height > wide_cand.height


def test_long_token_overflow_policy():
    long_token = "averyveryveryveryveryverylongtechnicaltokenwithoutspaces"
    policy = MeasurementPolicy(
        candidate_max_widths=[100.0],
        emergency_break_long_tokens=False,
    )
    m = measure_text(long_token, policy)
    cand = m.wrap_candidates[0]
    assert cand.had_overflow_token is True
    assert cand.had_emergency_break is False
    assert cand.line_count == 1
    assert cand.lines[0] == long_token


def test_long_token_emergency_break_policy():
    long_token = "averyveryveryveryveryverylongtechnicaltokenwithoutspaces"
    policy = MeasurementPolicy(
        candidate_max_widths=[100.0],
        emergency_break_long_tokens=True,
    )
    m = measure_text(long_token, policy)
    cand = m.wrap_candidates[0]
    assert cand.had_emergency_break is True
    assert cand.line_count > 1
    assert "".join(cand.lines) == long_token


# ---------------------------------------------------------------------------
# Math Measurement Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        "y = mx + b",
        "E = mc²",
        "∂L/∂w",
        "a/b",
        "x^2 + y^2",
        "e^{-x}",
        "x_1 + x_2",
        "α + β = θ",
    ],
)
def test_valid_math_expressions_measured(expr: str):
    m = measure_math(expr)
    assert m.width > 0.0
    assert m.height > 0.0
    assert m.minimum_readable_width > 0.0
    assert m.minimum_readable_height > 0.0
    assert m.expression == expr


def test_math_structural_flag():
    m_plain = measure_math("y = mx + b")
    assert m_plain.is_structural is False

    m_struct = measure_math("x^2 + y_1")
    assert m_struct.is_structural is True


def test_unsupported_complex_math_raises():
    unsupported_expressions = [
        r"\begin{matrix} 1 & 0 \\ 0 & 1 \end{matrix}",
        r"\int_{0}^{\infty} f(x) dx",
        r"\sum_{i=1}^{n} x_i",
        r"\sqrt{x^2 + y^2}",
        r"\frac{numerator}{denominator}",
    ]
    for expr in unsupported_expressions:
        with pytest.raises(MeasurementUnsupportedMathError) as exc_info:
            measure_math(expr)
        assert exc_info.value.code == "MEASUREMENT_UNSUPPORTED_MATH"


# ---------------------------------------------------------------------------
# Asset Measurement Tests
# ---------------------------------------------------------------------------


def test_valid_asset_measurement(sample_test_image: Path):
    m = measure_asset(sample_test_image)
    assert m.width == 200.0
    assert m.height == 100.0
    assert m.aspect_ratio == 2.0
    assert m.minimum_readable_width > 0.0
    assert m.minimum_readable_height > 0.0
    assert m.format.upper() == "PNG"


def test_missing_asset_raises(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist.png"
    with pytest.raises(MeasurementAssetNotFoundError) as exc_info:
        measure_asset(nonexistent)
    assert exc_info.value.code == "MEASUREMENT_ASSET_NOT_FOUND"


def test_corrupt_asset_raises(corrupt_test_image: Path):
    with pytest.raises(MeasurementInvalidAssetError) as exc_info:
        measure_asset(corrupt_test_image)
    assert exc_info.value.code == "MEASUREMENT_INVALID_ASSET"


# ---------------------------------------------------------------------------
# Icon Measurement Tests
# ---------------------------------------------------------------------------


def test_icon_measurement_deterministic():
    m = measure_icon("sparkles", MeasurementPolicy(preferred_font_size=24.0, minimum_font_size=14.0))
    assert m.name == "sparkles"
    assert m.width == 24.0
    assert m.height == 24.0
    assert m.aspect_ratio == 1.0
    assert m.minimum_readable_width == 14.0
    assert m.minimum_readable_height == 14.0
    assert m.em_size == 24.0


def test_empty_icon_name_rejected():
    with pytest.raises(MeasurementInvalidInputError) as exc_info:
        measure_icon("   ")
    assert exc_info.value.code == "MEASUREMENT_INVALID_INPUT"


# ---------------------------------------------------------------------------
# Node Dispatch Tests
# ---------------------------------------------------------------------------


def test_measure_node_dispatch_text():
    node = SceneNode(id="n_text", kind=NodeKind.TEXT, label="Hello LearnFlow")
    m = measure_node(node)
    assert isinstance(m, TextMeasurement)
    assert m.content == "Hello LearnFlow"


def test_measure_node_dispatch_concept():
    node = SceneNode(id="n_concept", kind=NodeKind.CONCEPT, label="Gradient Descent")
    m = measure_node(node)
    assert isinstance(m, TextMeasurement)
    assert m.content == "Gradient Descent"


def test_measure_node_dispatch_math():
    node = SceneNode(id="n_math", kind=NodeKind.MATH, content="E = mc²")
    m = measure_node(node)
    assert isinstance(m, MathMeasurement)
    assert m.expression == "E = mc²"


def test_measure_node_dispatch_equation():
    node = SceneNode(id="n_eq", kind=NodeKind.EQUATION, label="y = mx + b")
    m = measure_node(node)
    assert isinstance(m, MathMeasurement)
    assert m.expression == "y = mx + b"


def test_measure_node_dispatch_icon():
    node = SceneNode(id="n_icon", kind=NodeKind.ICON, label="lightbulb")
    m = measure_node(node)
    assert isinstance(m, IconMeasurement)
    assert m.name == "lightbulb"


def test_measure_node_dispatch_image(sample_test_image: Path):
    node = SceneNode(id="n_img", kind=NodeKind.IMAGE, content=str(sample_test_image))
    m = measure_node(node)
    assert isinstance(m, AssetMeasurement)
    assert m.width == 200.0


def test_measure_node_unsupported_kind_raises():
    node = SceneNode(id="n_shape", kind=NodeKind.SHAPE, label="Rectangle")
    with pytest.raises(MeasurementUnsupportedNodeError) as exc_info:
        measure_node(node)
    assert exc_info.value.code == "MEASUREMENT_UNSUPPORTED_NODE"


# ---------------------------------------------------------------------------
# Strict Validation & Finite Numbers (No NaN/Inf)
# ---------------------------------------------------------------------------


def test_measurement_models_reject_nan_and_inf():
    with pytest.raises(ValidationError):
        IntrinsicSize(
            width=float("nan"),
            height=50.0,
            minimum_readable_width=10.0,
            minimum_readable_height=10.0,
        )

    with pytest.raises(ValidationError):
        IntrinsicSize(
            width=float("inf"),
            height=50.0,
            minimum_readable_width=10.0,
            minimum_readable_height=10.0,
        )

    with pytest.raises(ValidationError):
        IntrinsicSize(
            width=100.0,
            height=-10.0,  # Negative height rejected
            minimum_readable_width=10.0,
            minimum_readable_height=10.0,
        )


def test_canonical_json_roundtrip_measurement():
    tm = measure_text("Canonical Roundtrip Serialization Test")
    dumped = canonical_json(tm)
    restored = TextMeasurement.model_validate_json(dumped)
    assert canonical_json(restored) == dumped


# ---------------------------------------------------------------------------
# Fixture Corpus Acceptance Test (55 cases)
# ---------------------------------------------------------------------------


def test_measurement_fixture_corpus_acceptance():
    corpus_path = Path("benchmarks/fixtures/v2/measurement_cases.json")
    assert corpus_path.is_file(), "Measurement fixture corpus must exist"

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    cases = corpus["cases"]
    assert len(cases) >= 40, f"Corpus must have at least 40 cases, got {len(cases)}"

    for case in cases:
        c_id = case["id"]
        c_type = case["type"]
        c_input = case["input"]

        if c_type == "text":
            m_text = measure_text(c_input)
            assert m_text.width > 0.0, f"Case {c_id}: width must be positive"
            assert m_text.height > 0.0, f"Case {c_id}: height must be positive"
            assert m_text.minimum_readable_width > 0.0, f"Case {c_id}: min width must be positive"
            assert m_text.minimum_readable_height > 0.0, f"Case {c_id}: min height must be positive"
            assert len(m_text.wrap_candidates) > 0, f"Case {c_id}: must generate wrap candidates"

        elif c_type == "math":
            m_math = measure_math(c_input)
            assert m_math.width > 0.0, f"Case {c_id}: math width must be positive"
            assert m_math.height > 0.0, f"Case {c_id}: math height must be positive"

        elif c_type == "icon":
            m_icon = measure_icon(c_input)
            assert m_icon.width > 0.0, f"Case {c_id}: icon width must be positive"
            assert m_icon.aspect_ratio == 1.0, f"Case {c_id}: icon aspect ratio must be 1.0"


# ---------------------------------------------------------------------------
# V2-02 Hardening Regression Tests
# ---------------------------------------------------------------------------


def test_reversed_font_size_range_rejected():
    # preferred=14, minimum=24 -> REJECT
    with pytest.raises(ValidationError):
        MeasurementPolicy(preferred_font_size=14.0, minimum_font_size=24.0)

    # preferred=24, minimum=14 -> PASS
    p_valid = MeasurementPolicy(preferred_font_size=24.0, minimum_font_size=14.0)
    assert p_valid.preferred_font_size == 24.0
    assert p_valid.minimum_font_size == 14.0

    # preferred=14, minimum=14 -> PASS
    p_equal = MeasurementPolicy(preferred_font_size=14.0, minimum_font_size=14.0)
    assert p_equal.preferred_font_size == 14.0
    assert p_equal.minimum_font_size == 14.0


def test_empty_candidate_widths_rejected():
    with pytest.raises(ValidationError):
        MeasurementPolicy(candidate_max_widths=[])


def test_candidate_widths_sorted_and_deduplicated():
    p = MeasurementPolicy(candidate_max_widths=[600, 300, 600])
    assert p.candidate_max_widths == [300.0, 600.0]

    p2 = MeasurementPolicy(candidate_max_widths=[1200, 400, 400, 800, 250])
    assert p2.candidate_max_widths == [250.0, 400.0, 800.0, 1200.0]


def test_single_hard_newline_preserved():
    m = measure_text("alpha\nbeta", MeasurementPolicy(candidate_max_widths=[2000]))
    assert m.wrap_candidates[0].lines == ["alpha", "beta"]
    assert m.lines == ["alpha", "beta"]


def test_multiple_hard_newlines_preserved():
    m = measure_text("line1\nline2\nline3", MeasurementPolicy(candidate_max_widths=[2000]))
    assert m.wrap_candidates[0].lines == ["line1", "line2", "line3"]


def test_blank_line_preserved():
    m = measure_text("title\n\nbody", MeasurementPolicy(candidate_max_widths=[2000]))
    assert m.wrap_candidates[0].lines == ["title", "", "body"]
    assert m.lines == ["title", "", "body"]


def test_vietnamese_hard_newline_preserved():
    text = "Giải thích quang hợp\nÁnh sáng → năng lượng"
    m = measure_text(text, MeasurementPolicy(candidate_max_widths=[2000]))
    assert m.wrap_candidates[0].lines == ["Giải thích quang hợp", "Ánh sáng → năng lượng"]
    assert m.lines == ["Giải thích quang hợp", "Ánh sáng → năng lượng"]


def test_soft_wrapping_inside_hard_line_segments():
    text = "Tiêu đề bài học\nĐây là một đoạn giải thích rất dài sẽ vượt quá độ rộng giới hạn của khung hình hiển thị"
    m = measure_text(text, MeasurementPolicy(candidate_max_widths=[250.0]))
    cand = m.wrap_candidates[0]
    # First line must remain the first segment
    assert cand.lines[0] == "Tiêu đề bài học"
    # Second segment must have been wrapped into multiple lines
    assert cand.line_count >= 3
    # Check that the tokens of segment 2 were preserved in order
    seg2_tokens = (" ".join(cand.lines[1:])).split()
    assert seg2_tokens == (
        "Đây là một đoạn giải thích rất dài sẽ vượt quá độ rộng giới hạn của khung hình hiển thị"
    ).split()


def test_long_token_fallback_with_hard_lines():
    long_tok = "averyveryveryveryveryverylongtechnicaltokenwithoutspaces"
    text = f"First Line\n{long_tok}\nThird Line"

    # With overflow allowed
    m_overflow = measure_text(
        text,
        MeasurementPolicy(candidate_max_widths=[150.0], emergency_break_long_tokens=False),
    )
    cand_of = m_overflow.wrap_candidates[0]
    assert cand_of.had_overflow_token is True
    assert cand_of.lines[0] == "First Line"
    assert cand_of.lines[1] == long_tok
    assert cand_of.lines[2] == "Third Line"

    # With emergency break
    m_break = measure_text(
        text,
        MeasurementPolicy(candidate_max_widths=[150.0], emergency_break_long_tokens=True),
    )
    cand_br = m_break.wrap_candidates[0]
    assert cand_br.had_emergency_break is True
    assert cand_br.lines[0] == "First Line"
    assert cand_br.lines[-1] == "Third Line"
    # The middle lines joined without spaces must reconstruct the original long token
    assert "".join(cand_br.lines[1:-1]) == long_tok

