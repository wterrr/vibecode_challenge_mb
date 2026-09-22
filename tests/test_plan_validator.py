"""Unit tests for lesson plan semantic validation and duration warning checks."""

import pytest
from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonColumn,
    ComparisonSpec,
    ConceptCardSpec,
    IllustrationSpec,
    LearningRequest,
    LessonPlan,
    ProcessActor,
    ProcessDiagramSpec,
    ProcessStep,
    ScenePlan,
)
from app.planning.validator import validate_lesson_plan


def make_valid_tcp_plan() -> LessonPlan:
    """Fixture: Valid 3-scene plan for TCP handshake (ProcessDiagram)."""
    return LessonPlan(
        title="Quá trình bắt tay 3 bước TCP",
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        learning_objective="Hiểu cơ chế thiết lập kết nối tin cậy giữa Client và Server qua TCP.",
        summary="TCP sử dụng SYN, SYN-ACK và ACK để đồng bộ sequence numbers trước khi truyền dữ liệu.",
        scenes=[
            ScenePlan(
                scene_id="s01_intro",
                title="Khái niệm bắt tay TCP",
                concept="TCP đảm bảo kết nối tin cậy trước khi truyền nhận dữ liệu.",
                narration="Trước khi truyền tải dữ liệu, giao thức TCP cần thiết lập một kết nối tin cậy giữa hai máy tính.",
                key_points=["Giao thức hướng kết nối", "Đảm bảo truyền tin cậy"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(
                    heading="Giao thức TCP",
                    points=["Đảm bảo tin cậy", "Đồng bộ số thứ tự", "Kiểm soát luồng"],
                ),
            ),
            ScenePlan(
                scene_id="s02_handshake_flow",
                title="Ba bước bắt tay",
                concept="Trao đổi các gói tin SYN, SYN-ACK và ACK giữa Client và Server.",
                narration="Client gửi gói tin SYN. Server phản hồi bằng gói SYN-ACK. Cuối cùng, Client gửi lại ACK để hoàn tất.",
                key_points=["Bước 1: SYN", "Bước 2: SYN-ACK", "Bước 3: ACK"],
                visual_intent=VisualIntent.PROCESS_DIAGRAM,
                visual_spec=ProcessDiagramSpec(
                    title="Tiến trình bắt tay 3 bước",
                    actors=[
                        ProcessActor(id="client", label="Client"),
                        ProcessActor(id="server", label="Server"),
                    ],
                    steps=[
                        ProcessStep(order=1, from_actor="client", to_actor="server", label="SYN"),
                        ProcessStep(order=2, from_actor="server", to_actor="client", label="SYN-ACK"),
                        ProcessStep(order=3, from_actor="client", to_actor="server", label="ACK"),
                    ],
                ),
            ),
            ScenePlan(
                scene_id="s03_summary",
                title="Kết luận",
                concept="Kết nối được thiết lập sẵn sàng truyền dữ liệu.",
                narration="Sau khi ba bước hoàn tất, kết nối sẵn sàng để truyền tải thông tin an toàn và chính xác.",
                key_points=["Kết nối sẵn sàng", "Sẵn sàng truyền dữ liệu"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(
                    heading="Tổng kết",
                    points=["Đồng bộ thành công", "Sẵn sàng truyền tin"],
                ),
            ),
        ],
    )


def make_valid_photosynthesis_plan() -> LessonPlan:
    """Fixture: Valid 3-scene plan for photosynthesis (Process + Illustration)."""
    return LessonPlan(
        title="Quá trình quang hợp ở thực vật",
        topic="Explain photosynthesis to a middle-school student.",
        audience="Student",
        language="vi",
        learning_objective="Hiểu cách cây xanh chuyển đổi ánh sáng mặt trời thành năng lượng.",
        summary="Cây xanh hấp thụ ánh sáng, nước và CO2 để tạo ra glucose và giải phóng oxy.",
        scenes=[
            ScenePlan(
                scene_id="s01_leaf_structure",
                title="Lá cây và lục lạp",
                concept="Lục lạp trong lá cây chứa diệp lục hấp thụ ánh sáng.",
                narration="Lá cây có hàng triệu nhà máy nhỏ gọi là lục lạp giúp hấp thụ ánh sáng mặt trời mỗi ngày.",
                key_points=["Lục lạp", "Chất diệp lục"],
                visual_intent=VisualIntent.ILLUSTRATION,
                visual_spec=IllustrationSpec(
                    prompt="A vibrant green leaf absorbing bright sunlight with visible cellular chloroplasts.",
                    fallback_heading="Cấu trúc lục lạp",
                    fallback_points=["Nơi quang hợp diễn ra", "Hấp thụ ánh sáng mặt trời"],
                ),
            ),
            ScenePlan(
                scene_id="s02_chemical_process",
                title="Phản ứng tạo năng lượng",
                concept="Nước và khí carbon dioxide phản ứng tạo thành đường glucose và oxy.",
                narration="Dưới tác dụng của ánh sáng, nước và khí CO2 phản ứng để tạo ra đường nuôi cây và khí oxy nuôi sống sự sống.",
                key_points=["Đầu vào: Nước + CO2", "Đầu ra: Glucose + O2"],
                visual_intent=VisualIntent.PROCESS_DIAGRAM,
                visual_spec=ProcessDiagramSpec(
                    title="Phản ứng quang hợp",
                    actors=[
                        ProcessActor(id="inputs", label="Nước & CO2"),
                        ProcessActor(id="leaf", label="Lục lạp"),
                        ProcessActor(id="outputs", label="Glucose & O2"),
                    ],
                    steps=[
                        ProcessStep(order=1, from_actor="inputs", to_actor="leaf", label="Hấp thụ nguyên liệu"),
                        ProcessStep(order=2, from_actor="leaf", to_actor="outputs", label="Chuyển hóa năng lượng"),
                    ],
                ),
            ),
            ScenePlan(
                scene_id="s03_importance",
                title="Ý nghĩa của quang hợp",
                concept="Cung cấp thức ăn và oxy cho toàn bộ sinh quyển Trái Đất.",
                narration="Nhờ quang hợp, hành tinh của chúng ta có nguồn khí oxy trong lành và thức ăn dồi dào cho muôn loài.",
                key_points=["Cung cấp oxy", "Duy trì sự sống"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(
                    heading="Tầm quan trọng",
                    points=["Tạo nguồn oxy", "Cung cấp dinh dưỡng cho sinh quyển"],
                ),
            ),
        ],
    )


def make_valid_ram_ssd_plan() -> LessonPlan:
    """Fixture: Valid 3-scene plan for RAM vs SSD (Comparison)."""
    return LessonPlan(
        title="RAM và SSD: Khác biệt cốt lõi",
        topic="RAM vs SSD for a beginner.",
        audience="Beginner",
        language="vi",
        learning_objective="Phân biệt vai trò của bộ nhớ tạm thời RAM và ổ đĩa lưu trữ SSD.",
        summary="RAM là bàn làm việc tốc độ cao, còn SSD là tủ chứa tài liệu lâu dài.",
        scenes=[
            ScenePlan(
                scene_id="s01_intro",
                title="Hai loại bộ nhớ máy tính",
                concept="Máy tính cần cả bộ nhớ xử lý nhanh và bộ nhớ lưu trữ lâu dài.",
                narration="Máy tính của bạn cần cả hai thành phần: một nơi để làm việc tức thì và một nơi cất giữ dữ liệu dài lâu.",
                key_points=["Bộ nhớ tạm thời", "Bộ nhớ lưu trữ"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(
                    heading="Bộ nhớ máy tính",
                    points=["Xử lý tạm thời", "Lưu trữ vĩnh viễn"],
                ),
            ),
            ScenePlan(
                scene_id="s02_comparison",
                title="So sánh chi tiết RAM vs SSD",
                concept="RAM cực nhanh nhưng mất dữ liệu khi tắt máy; SSD chậm hơn nhưng lưu trữ vĩnh viễn.",
                narration="RAM có tốc độ siêu nhanh nhưng mất dữ liệu khi mất điện. SSD lưu trữ lâu dài an toàn dù tốc độ chậm hơn RAM.",
                key_points=["RAM: Tốc độ cao, tạm thời", "SSD: Dung lượng lớn, bền bỉ"],
                visual_intent=VisualIntent.COMPARISON,
                visual_spec=ComparisonSpec(
                    title="Bảng so sánh RAM vs SSD",
                    columns=[
                        ComparisonColumn(
                            title="RAM",
                            subtitle="Bộ nhớ truy xuất ngẫu nhiên",
                            points=["Rất nhanh", "Mất điện là mất dữ liệu", "Dung lượng nhỏ hơn"],
                        ),
                        ComparisonColumn(
                            title="SSD",
                            subtitle="Ổ lưu trữ thể rắn",
                            points=["Tốc độ vừa phải", "Giữ dữ liệu an toàn", "Dung lượng lớn"],
                        ),
                    ],
                ),
            ),
            ScenePlan(
                scene_id="s03_takeaway",
                title="Lời khuyên khi nâng cấp",
                concept="Nâng cấp RAM khi cần chạy đa nhiệm, nâng cấp SSD khi hết dung lượng chứa file.",
                narration="Nếu máy chạy chậm khi mở nhiều app, hãy thêm RAM. Nếu hết chỗ lưu file hoặc muốn khởi động nhanh, hãy chọn SSD lớn hơn.",
                key_points=["Đa nhiệm -> RAM", "Lưu trữ -> SSD"],
                visual_intent=VisualIntent.CONCEPT_CARD,
                visual_spec=ConceptCardSpec(
                    heading="Tóm tắt lựa chọn",
                    points=["Cần đa nhiệm -> nâng cấp RAM", "Cần chỗ lưu trữ -> nâng cấp SSD"],
                ),
            ),
        ],
    )


def test_valid_tcp_plan_has_no_errors() -> None:
    """Valid TCP handshake plan produces zero semantic errors."""
    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        audience="Developer",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_tcp_plan()
    issues = validate_lesson_plan(request, plan)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0


def test_valid_photosynthesis_plan_has_no_errors() -> None:
    """Valid photosynthesis plan produces zero semantic errors."""
    request = LearningRequest(
        topic="Explain photosynthesis to a middle-school student.",
        audience="Student",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_photosynthesis_plan()
    issues = validate_lesson_plan(request, plan)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0


def test_valid_ram_ssd_plan_has_no_errors() -> None:
    """Valid RAM vs SSD comparison plan produces zero semantic errors."""
    request = LearningRequest(
        topic="RAM vs SSD for a beginner.",
        audience="Beginner",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_ram_ssd_plan()
    issues = validate_lesson_plan(request, plan)
    errors = [i for i in issues if i.severity == "error"]
    assert len(errors) == 0


def test_validator_detects_wrong_language() -> None:
    """Mismatch between requested language and plan language yields an error."""
    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="en",
        target_duration_seconds=60,
    )
    plan = make_valid_tcp_plan()  # plan.language is "vi"
    issues = validate_lesson_plan(request, plan)
    error_codes = [i.code for i in issues if i.severity == "error"]
    assert "plan_language_mismatch" in error_codes


def test_validator_detects_unrelated_topic() -> None:
    """Completely unrelated plan topic yields plan_topic_mismatch error."""
    request = LearningRequest(
        topic="Quá trình quang hợp ở thực vật",
        language="vi",
        target_duration_seconds=60,
    )
    # Plan is entirely about TCP handshake
    plan = make_valid_tcp_plan()
    issues = validate_lesson_plan(request, plan)
    error_codes = [i.code for i in issues if i.severity == "error"]
    assert "plan_topic_mismatch" in error_codes


def test_validator_detects_paraphrased_topic_as_valid() -> None:
    """Legitimately paraphrased topic passes topic relevance heuristic."""
    request = LearningRequest(
        topic="TCP Handshake connection flow",
        audience="Developer",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_tcp_plan()
    issues = validate_lesson_plan(request, plan)
    error_codes = [i.code for i in issues if i.severity == "error"]
    assert "plan_topic_mismatch" not in error_codes


def test_validator_repeated_scene_titles_yields_warning() -> None:
    """Repeated scene titles yield a warning rather than blocking error."""
    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_tcp_plan()
    # Duplicate title across scene 1 and scene 3
    plan.scenes[2].title = plan.scenes[0].title

    issues = validate_lesson_plan(request, plan)
    warning_codes = [i.code for i in issues if i.severity == "warning"]
    error_codes = [i.code for i in issues if i.severity == "error"]

    assert "repeated_scene_titles" in warning_codes
    assert len(error_codes) == 0


def test_validator_too_much_narration_yields_warning() -> None:
    """Overly verbose narration for 60s target yields a warning."""
    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=60,
    )
    plan = make_valid_tcp_plan()
    # Inject 250 words into narration
    plan.scenes[0].narration = "Từ này lặp lại " * 80

    issues = validate_lesson_plan(request, plan)
    warning_codes = [i.code for i in issues if i.severity == "warning"]
    assert "narration_likely_too_long" in warning_codes


def test_validator_too_little_narration_yields_warning() -> None:
    """Extremely sparse narration for 120s target yields a warning."""
    request = LearningRequest(
        topic="How does the TCP three-way handshake work?",
        language="vi",
        target_duration_seconds=120,
    )
    plan = make_valid_tcp_plan()
    plan.scenes[0].narration = "Rất ngắn."
    plan.scenes[1].narration = "Quá ngắn."
    plan.scenes[2].narration = "Xong."

    issues = validate_lesson_plan(request, plan)
    warning_codes = [i.code for i in issues if i.severity == "warning"]
    assert "narration_likely_too_short" in warning_codes
