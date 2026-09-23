"""Pre-validated demonstration lesson plans for offline demo mode."""

from app.domain.enums import VisualIntent
from app.domain.lesson import (
    ComparisonColumn,
    ComparisonSpec,
    ConceptCardSpec,
    LessonPlan,
    ProcessActor,
    ProcessDiagramSpec,
    ProcessStep,
    ScenePlan,
)

DEMO_TCP_PLAN = LessonPlan(
    schema_version="1.0",
    title="Cơ chế bắt tay 3 bước TCP",
    topic="How does the TCP three-way handshake work?",
    audience="Developer",
    language="vi",
    learning_objective="Hiểu quy trình SYN, SYN-ACK, ACK để thiết lập kết nối tin cậy.",
    summary="TCP sử dụng quy trình bắt tay 3 bước nhằm đồng bộ số thứ tự và kiểm tra kết nối hai chiều.",
    scenes=[
        ScenePlan(
            scene_id="s01_intro",
            title="Khái niệm kết nối TCP",
            concept="TCP là giao thức hướng kết nối đảm bảo dữ liệu truyền tải tin cậy và tuần tự.",
            narration="Trước khi truyền dữ liệu qua TCP, máy khách và máy chủ phải thiết lập kết nối tin cậy.",
            key_points=[
                "Giao thức hướng kết nối",
                "Đảm bảo truyền dữ liệu chính xác",
                "Đồng bộ sequence number",
            ],
            visual_intent=VisualIntent.CONCEPT_CARD,
            visual_spec=ConceptCardSpec(
                heading="TCP Handshake là gì?",
                points=[
                    "Giao thức tầng giao vận đảm bảo tin cậy tuyệt đối",
                    "Đồng bộ số thứ tự truyền nhận giữa hai đầu cuối",
                    "Khởi tạo trước khi truyền tải gói tin HTTP hoặc HTTPS",
                ],
                emphasis=["Hướng kết nối", "Tin cậy 100%", "Đồng bộ"],
            ),
            duration_seconds=20,
        ),
        ScenePlan(
            scene_id="s02_steps",
            title="Quy trình bắt tay 3 bước",
            concept="Ba gói tin trao đổi lần lượt giữa máy khách và máy chủ.",
            narration="Máy khách gửi gói tin SYN. Máy chủ đáp lại bằng SYN-ACK. Cuối cùng máy khách gửi ACK xác nhận.",
            key_points=[
                "Bước 1: Client gửi SYN",
                "Bước 2: Server gửi SYN-ACK",
                "Bước 3: Client gửi ACK",
            ],
            visual_intent=VisualIntent.PROCESS_DIAGRAM,
            visual_spec=ProcessDiagramSpec(
                title="Luồng trao đổi gói tin TCP",
                actors=[
                    ProcessActor(id="client", label="Client"),
                    ProcessActor(id="server", label="Server"),
                ],
                steps=[
                    ProcessStep(
                        order=1,
                        from_actor="client",
                        to_actor="server",
                        label="SYN (seq=100)",
                        description="Client đề xuất mở kết nối với sequence khởi tạo 100.",
                    ),
                    ProcessStep(
                        order=2,
                        from_actor="server",
                        to_actor="client",
                        label="SYN-ACK (seq=300, ack=101)",
                        description="Server xác nhận và gửi sequence riêng của Server.",
                    ),
                    ProcessStep(
                        order=3,
                        from_actor="client",
                        to_actor="server",
                        label="ACK (ack=301)",
                        description="Client xác nhận. Kết nối chính thức sẵn sàng.",
                    ),
                ],
            ),
            duration_seconds=35,
        ),
        ScenePlan(
            scene_id="s03_comparison",
            title="So sánh TCP và UDP",
            concept="Sự đánh đổi giữa độ tin cậy và tốc độ truyền tải.",
            narration="Khác với TCP cần bắt tay để đảm bảo tin cậy, giao thức UDP gửi dữ liệu trực tiếp giúp tối ưu tốc độ.",
            key_points=[
                "TCP đảm bảo độ tin cậy cao",
                "UDP tối ưu độ trễ thấp",
            ],
            visual_intent=VisualIntent.COMPARISON,
            visual_spec=ComparisonSpec(
                title="So sánh giao thức: TCP vs UDP",
                columns=[
                    ComparisonColumn(
                        title="TCP (Có bắt tay)",
                        subtitle="Độ tin cậy tuyệt đối",
                        points=[
                            "Bắt buộc 3 bước bắt tay ban đầu",
                            "Tự động truyền lại gói tin bị mất",
                            "Phù hợp: Web, Tệp tin, Email",
                        ],
                    ),
                    ComparisonColumn(
                        title="UDP (Không bắt tay)",
                        subtitle="Tốc độ tối đa",
                        points=[
                            "Truyền dữ liệu ngay lập tức",
                            "Chấp nhận mất mát dữ liệu",
                            "Phù hợp: Live Stream, Game, Voice",
                        ],
                    ),
                ],
            ),
            duration_seconds=25,
        ),
    ],
)

DEMO_PHOTOSYNTHESIS_PLAN = LessonPlan(
    schema_version="1.0",
    title="Quá trình quang hợp ở thực vật",
    topic="Explain photosynthesis to a middle-school student.",
    audience="Student",
    language="vi",
    learning_objective="Hiểu cách cây xanh chuyển hóa năng lượng mặt trời thành năng lượng hóa học.",
    summary="Cây xanh hấp thụ nước và khí carbon dioxide dưới ánh sáng mặt trời để tạo ra glucose và oxy.",
    scenes=[
        ScenePlan(
            scene_id="s01_concept",
            title="Quang hợp là gì?",
            concept="Quang hợp là quá trình thực vật tự tổng hợp thức ăn từ ánh sáng mặt trời.",
            narration="Quang hợp là quá trình kì diệu giúp cây xanh chuyển hóa năng lượng ánh sáng thành chất hữu cơ.",
            key_points=[
                "Diễn ra tại lục lạp của lá cây",
                "Sử dụng sắc tố diệp lục",
                "Nuôi sống sinh quyển Trái Đất",
            ],
            visual_intent=VisualIntent.CONCEPT_CARD,
            visual_spec=ConceptCardSpec(
                heading="Bản chất của Quang Hợp",
                points=[
                    "Nguyên liệu đầu vào: Nước, khí CO2 và ánh sáng",
                    "Nơi diễn ra: Bào quan lục lạp chứa chất diệp lục",
                    "Sản phẩm tạo thành: Đường Glucose và khí Oxy",
                ],
                emphasis=["Lục lạp", "Ánh sáng", "Nuôi dưỡng Trái Đất"],
            ),
            duration_seconds=25,
        ),
        ScenePlan(
            scene_id="s02_steps",
            title="Các giai đoạn quang hợp",
            concept="Hai pha chính: Pha sáng và Pha tối diễn ra tuần tự.",
            narration="Pha sáng hấp thụ năng lượng mặt trời để phân tách nước, sau đó pha tối sử dụng năng lượng này để cố định carbon dioxide.",
            key_points=[
                "Pha sáng: Hấp thụ photon và giải phóng oxy",
                "Pha tối: Cố định khí carbon thành đường",
            ],
            visual_intent=VisualIntent.PROCESS_DIAGRAM,
            visual_spec=ProcessDiagramSpec(
                title="Chu trình chuyển hóa năng lượng",
                actors=[
                    ProcessActor(id="sun", label="Ánh sáng Mặt Trời"),
                    ProcessActor(id="chloroplast", label="Lục lạp (Pha Sáng)"),
                    ProcessActor(id="calvin", label="Chu trình Calvin (Pha Tối)"),
                ],
                steps=[
                    ProcessStep(
                        order=1,
                        from_actor="sun",
                        to_actor="chloroplast",
                        label="Hấp thụ ánh sáng",
                        description="Năng lượng photon kích hoạt diệp lục phân tách phân tử nước.",
                    ),
                    ProcessStep(
                        order=2,
                        from_actor="chloroplast",
                        to_actor="calvin",
                        label="Truyền ATP & NADPH",
                        description="Năng lượng hóa học từ pha sáng được nạp vào chu trình pha tối.",
                    ),
                    ProcessStep(
                        order=3,
                        from_actor="calvin",
                        to_actor="calvin",
                        label="Tạo đường Glucose",
                        description="Cố định CO2 thành phân tử đường nuôi dưỡng toàn bộ cây.",
                    ),
                ],
            ),
            duration_seconds=35,
        ),
        ScenePlan(
            scene_id="s03_comparison",
            title="So sánh Quang hợp và Hô hấp",
            concept="Mối liên hệ bổ trợ giữa hai quá trình trao đổi chất của sinh vật.",
            narration="Nếu quang hợp tích lũy năng lượng và thải ra oxy thì hô hấp phân giải năng lượng và giải phóng khí carbon dioxide.",
            key_points=[
                "Quang hợp tích lũy năng lượng",
                "Hô hấp giải phóng năng lượng",
            ],
            visual_intent=VisualIntent.COMPARISON,
            visual_spec=ComparisonSpec(
                title="Quang hợp vs Hô hấp tế bào",
                columns=[
                    ComparisonColumn(
                        title="Quang hợp",
                        subtitle="Tích lũy năng lượng",
                        points=[
                            "Chỉ xảy ra khi có ánh sáng",
                            "Hấp thụ CO2, giải phóng O2",
                            "Tổng hợp chất hữu cơ (Glucose)",
                        ],
                    ),
                    ComparisonColumn(
                        title="Hô hấp tế bào",
                        subtitle="Giải phóng năng lượng",
                        points=[
                            "Diễn ra liên tục ngày và đêm",
                            "Hấp thụ O2, giải phóng CO2",
                            "Phân giải chất hữu cơ để lấy ATP",
                        ],
                    ),
                ],
            ),
            duration_seconds=25,
        ),
    ],
)

DEMO_RAM_SSD_PLAN = LessonPlan(
    schema_version="1.0",
    title="So sánh RAM và SSD",
    topic="RAM vs SSD for a beginner.",
    audience="Beginner",
    language="vi",
    learning_objective="Phân biệt sự khác nhau giữa bộ nhớ tạm thời RAM và ổ lưu trữ bền vững SSD.",
    summary="RAM lưu trữ dữ liệu tạm thời với tốc độ siêu cao, trong khi SSD lưu trữ dữ liệu lâu dài ngay cả khi tắt máy.",
    scenes=[
        ScenePlan(
            scene_id="s01_intro",
            title="Khái niệm RAM và SSD",
            concept="Hai loại bộ nhớ cốt lõi đóng vai trò khác biệt trong máy tính.",
            narration="Để máy tính hoạt động trơn tru, máy tính cần cả bộ nhớ ngắn hạn tốc độ cao là RAM và kho chứa dữ liệu dài hạn là SSD.",
            key_points=[
                "RAM là bộ nhớ truy xuất ngẫu nhiên",
                "SSD là ổ đĩa thể rắn bền vững",
            ],
            visual_intent=VisualIntent.CONCEPT_CARD,
            visual_spec=ConceptCardSpec(
                heading="Vai trò của RAM và SSD",
                points=[
                    "RAM: Bàn làm việc tạm thời lưu dữ liệu chương trình đang chạy",
                    "SSD: Tủ tài liệu lưu trữ toàn bộ hệ điều hành và tệp tin",
                    "Bộ đôi phối hợp tạo nên tốc độ xử lý của máy tính",
                ],
                emphasis=["Bộ nhớ ngắn hạn", "Bộ nhớ dài hạn", "Tối ưu hiệu năng"],
            ),
            duration_seconds=22,
        ),
        ScenePlan(
            scene_id="s02_flow",
            title="Quy trình tải dữ liệu vào RAM",
            concept="Dữ liệu di chuyển từ ổ SSD vào RAM để bộ xử lý CPU thao tác nhanh chóng.",
            narration="Khi bạn mở một ứng dụng, máy tính sẽ nạp tệp từ ổ SSD sang RAM để bộ vi xử lý truy cập tức thời.",
            key_points=[
                "Dữ liệu được đọc từ SSD",
                "Chuyển vào bộ nhớ RAM",
                "CPU xử lý trực tiếp trên RAM",
            ],
            visual_intent=VisualIntent.PROCESS_DIAGRAM,
            visual_spec=ProcessDiagramSpec(
                title="Luồng nạp dữ liệu từ SSD vào RAM",
                actors=[
                    ProcessActor(id="ssd", label="Ổ đĩa SSD (Lưu trữ)"),
                    ProcessActor(id="ram", label="Bộ nhớ RAM (Tạm thời)"),
                    ProcessActor(id="cpu", label="Bộ vi xử lý CPU"),
                ],
                steps=[
                    ProcessStep(
                        order=1,
                        from_actor="ssd",
                        to_actor="ram",
                        label="Khởi chạy ứng dụng",
                        description="Hệ điều hành đọc mã nguồn ứng dụng từ SSD và nạp vào RAM.",
                    ),
                    ProcessStep(
                        order=2,
                        from_actor="ram",
                        to_actor="cpu",
                        label="Truy xuất tốc độ cực cao",
                        description="CPU đọc dữ liệu trực tiếp từ RAM với độ trễ nano giây.",
                    ),
                    ProcessStep(
                        order=3,
                        from_actor="ram",
                        to_actor="ssd",
                        label="Lưu kết quả (Ctrl+S)",
                        description="Khi bạn nhấn lưu, dữ liệu được ghi bền vững trở lại SSD.",
                    ),
                ],
            ),
            duration_seconds=35,
        ),
        ScenePlan(
            scene_id="s03_comparison",
            title="Bảng so sánh chi tiết: RAM vs SSD",
            concept="Khác biệt cốt lõi về tốc độ, giá thành và khả năng giữ dữ liệu.",
            narration="Tóm lại, RAM siêu nhanh nhưng mất dữ liệu khi mất điện, còn SSD lưu trữ vĩnh viễn với dung lượng lớn hơn nhiều.",
            key_points=[
                "RAM: Tốc độ cao, dễ bay hơi",
                "SSD: Bền vững, dung lượng lớn",
            ],
            visual_intent=VisualIntent.COMPARISON,
            visual_spec=ComparisonSpec(
                title="Đặc tính kỹ thuật: RAM vs SSD",
                columns=[
                    ComparisonColumn(
                        title="RAM (Bộ nhớ trong)",
                        subtitle="Tốc độ tức thời",
                        points=[
                            "Tốc độ đọc ghi lên tới hàng chục GB/s",
                            "Mất dữ liệu khi ngắt nguồn điện",
                            "Dung lượng thông dụng: 8GB - 64GB",
                        ],
                    ),
                    ComparisonColumn(
                        title="SSD (Ổ cứng thể rắn)",
                        subtitle="Lưu trữ dài hạn",
                        points=[
                            "Tốc độ đọc ghi từ 500MB/s đến 7GB/s",
                            "Giữ nguyên dữ liệu khi ngắt điện",
                            "Dung lượng thông dụng: 256GB - 2TB",
                        ],
                    ),
                ],
            ),
            duration_seconds=28,
        ),
    ],
)
