"""Generator script for LearnFlow V2 layout test fixtures.

Produces:
1. benchmarks/fixtures/v2/layout_simple_cases.json (32 valid cases)
2. benchmarks/fixtures/v2/layout_invalid_cases.json (8 invalid/UNSAT cases)
"""

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from learnflow_v2.layout import (
    LayoutItemInput,
    LayoutStrategy,
    solve_layout,
    validate_layout_graph,
)
from learnflow_v2.core.errors import LayoutUnsatisfiableError


def generate_valid_fixtures() -> list[dict]:
    cases = []
    case_idx = 1

    # 1. CONCEPT_CARD (8 cases)
    # Profile x Language x Length
    for profile in ["16:9", "9:16"]:
        for lang, title, body in [
            ("en", "Concept: Quantum Superposition", "A quantum system remains in all possible states until measured."),
            ("vi", "Khái niệm: Quang hợp", "Quá trình biến đổi năng lượng ánh sáng thành năng lượng hóa học."),
        ]:
            for length, body_text in [("short", body[:30]), ("moderate", body)]:
                # Approximate text bounds
                w_title = 320.0 if lang == "en" else 300.0
                h_title = 36.0
                w_content = 360.0 if length == "short" else 480.0
                h_content = 120.0 if length == "short" else 200.0
                if profile == "9:16":
                    w_title = min(w_title, 400.0)
                    w_content = min(w_content, 420.0)

                cid = f"concept_card_{profile.replace(':', '_')}_{lang}_{length}"
                cases.append({
                    "case_id": cid,
                    "strategy": "CONCEPT_CARD",
                    "profile": profile,
                    "language": lang,
                    "items": [
                        {"node_id": "title_node", "role": "title", "min_width": w_title, "min_height": h_title},
                        {"node_id": "content_node", "role": "content", "min_width": w_content, "min_height": h_content},
                    ],
                    "expected_invariants": {
                        "boxes_count": 2,
                        "title_zone": "TITLE",
                        "content_zone": "CONTENT",
                    },
                })
                case_idx += 1

    # 2. COMPARISON (8 cases)
    for profile in ["16:9", "9:16"]:
        for lang, l_title, r_title in [
            ("en", "RAM (Volatile)", "SSD (Persistent)"),
            ("vi", "Bộ nhớ RAM", "Ổ cứng SSD"),
        ]:
            for length in ["short", "moderate"]:
                w_item = 220.0 if length == "short" else 280.0
                h_item = 140.0 if length == "short" else 200.0
                if profile == "9:16":
                    w_item = 180.0 if length == "short" else 220.0

                cid = f"comparison_{profile.replace(':', '_')}_{lang}_{length}"
                cases.append({
                    "case_id": cid,
                    "strategy": "COMPARISON",
                    "profile": profile,
                    "language": lang,
                    "items": [
                        {"node_id": "left_card", "role": "left", "min_width": w_item, "min_height": h_item},
                        {"node_id": "right_card", "role": "right", "min_width": w_item, "min_height": h_item},
                    ],
                    "expected_invariants": {
                        "boxes_count": 2,
                        "columns_non_overlapping": True,
                        "equal_widths": True,
                        "mirror_symmetry": True,
                    },
                })
                case_idx += 1

    # 3. IMAGE_TEXT (8 cases)
    for profile in ["16:9", "9:16"]:
        for lang, txt in [
            ("en", "Chloroplasts absorb solar photons to drive ATP synthesis."),
            ("vi", "Lục lạp hấp thụ photon ánh sáng mặt trời để tổng hợp ATP."),
        ]:
            for length in ["short", "moderate"]:
                img_w = 260.0 if profile == "16:9" else 280.0
                img_h = 180.0 if profile == "16:9" else 180.0
                txt_w = 240.0 if length == "short" else 320.0
                txt_h = 100.0 if length == "short" else 160.0
                if profile == "9:16":
                    txt_w = 300.0

                cid = f"image_text_{profile.replace(':', '_')}_{lang}_{length}"
                cases.append({
                    "case_id": cid,
                    "strategy": "IMAGE_TEXT",
                    "profile": profile,
                    "language": lang,
                    "items": [
                        {"node_id": "img_node", "role": "image", "min_width": img_w, "min_height": img_h, "aspect_ratio": 1.44},
                        {"node_id": "text_node", "role": "text", "min_width": txt_w, "min_height": txt_h},
                    ],
                    "expected_invariants": {
                        "boxes_count": 2,
                        "non_overlapping": True,
                    },
                })
                case_idx += 1

    # 4. QUOTE (8 cases)
    for profile in ["16:9", "9:16"]:
        for lang, quote, author in [
            ("en", "Simplicity is prerequisite for reliability.", "Edsger W. Dijkstra"),
            ("vi", "Học, học nữa, học mãi.", "V. I. Lênin"),
        ]:
            for has_attr in [False, True]:
                q_w = 340.0 if lang == "en" else 280.0
                q_h = 80.0
                cid = f"quote_{profile.replace(':', '_')}_{lang}_{'with_attr' if has_attr else 'solo'}"
                items = [
                    {"node_id": "quote_text", "role": "quote", "min_width": q_w, "min_height": q_h},
                ]
                if has_attr:
                    items.append({
                        "node_id": "quote_author",
                        "role": "attribution",
                        "min_width": 180.0,
                        "min_height": 30.0,
                    })
                cases.append({
                    "case_id": cid,
                    "strategy": "QUOTE",
                    "profile": profile,
                    "language": lang,
                    "items": items,
                    "expected_invariants": {
                        "boxes_count": len(items),
                        "centered": True,
                    },
                })
                case_idx += 1

    return cases


def generate_invalid_fixtures() -> list[dict]:
    return [
        {
            "case_id": "unsat_single_item_wider_than_content",
            "strategy": "CONCEPT_CARD",
            "profile": "16:9",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "min_width exceeds content zone width (2000 > 1152)",
            "items": [
                {"node_id": "huge_node", "role": "content", "min_width": 2000.0, "min_height": 100.0}
            ],
        },
        {
            "case_id": "unsat_single_item_taller_than_content",
            "strategy": "CONCEPT_CARD",
            "profile": "16:9",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "min_height exceeds content zone height (1000 > 453.6)",
            "items": [
                {"node_id": "tall_node", "role": "content", "min_width": 300.0, "min_height": 1000.0}
            ],
        },
        {
            "case_id": "unsat_comparison_two_widths_exceed_content",
            "strategy": "COMPARISON",
            "profile": "16:9",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "left.min_width + right.min_width + gutter > content.width (600 + 600 + 32 > 1152)",
            "items": [
                {"node_id": "c1", "role": "left", "min_width": 600.0, "min_height": 150.0},
                {"node_id": "c2", "role": "right", "min_width": 600.0, "min_height": 150.0},
            ],
        },
        {
            "case_id": "unsat_comparison_portrait_widths_exceed_safe_w",
            "strategy": "COMPARISON",
            "profile": "9:16",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "left and right in portrait exceed safe width (350 + 350 + 20 > 648)",
            "items": [
                {"node_id": "c1", "role": "left", "min_width": 350.0, "min_height": 100.0},
                {"node_id": "c2", "role": "right", "min_width": 350.0, "min_height": 100.0},
            ],
        },
        {
            "case_id": "unsat_portrait_stacked_heights_exceed_content",
            "strategy": "IMAGE_TEXT",
            "profile": "9:16",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "image height + text height + gutter > content zone height (500 + 500 + 20 > 832)",
            "items": [
                {"node_id": "img", "role": "image", "min_width": 250.0, "min_height": 500.0},
                {"node_id": "txt", "role": "text", "min_width": 250.0, "min_height": 500.0},
            ],
        },
        {
            "case_id": "unsat_portrait_item_wider_than_frame",
            "strategy": "CONCEPT_CARD",
            "profile": "9:16",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "item wider than entire portrait frame (800 > 720)",
            "items": [
                {"node_id": "w_over", "role": "content", "min_width": 800.0, "min_height": 100.0}
            ],
        },
        {
            "case_id": "unsat_title_taller_than_title_zone",
            "strategy": "CONCEPT_CARD",
            "profile": "16:9",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "title height exceeds title zone height (200 > 97.2)",
            "items": [
                {"node_id": "big_title", "role": "title", "min_width": 200.0, "min_height": 200.0},
                {"node_id": "ok_content", "role": "content", "min_width": 200.0, "min_height": 100.0},
            ],
        },
        {
            "case_id": "unsat_quote_exceeds_max_bounded_width",
            "strategy": "QUOTE",
            "profile": "16:9",
            "expected_error": "LAYOUT_UNSATISFIABLE",
            "reason": "quote min width exceeds 90% content zone width (1100 > 1036.8)",
            "items": [
                {"node_id": "wide_quote", "role": "quote", "min_width": 1100.0, "min_height": 60.0}
            ],
        },
    ]


def main():
    root = Path(__file__).resolve().parent.parent
    fixtures_dir = root / "benchmarks" / "fixtures" / "v2"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    valid_cases = generate_valid_fixtures()
    invalid_cases = generate_invalid_fixtures()

    print(f"Valid cases to write: {len(valid_cases)}")
    for c in valid_cases:
        items = [
            LayoutItemInput(
                node_id=it["node_id"],
                role=it["role"],
                min_width=it["min_width"],
                min_height=it["min_height"],
                aspect_ratio=it.get("aspect_ratio"),
            )
            for it in c["items"]
        ]
        lg = solve_layout(c["case_id"], c["strategy"], c["profile"], items)
        rep = validate_layout_graph(lg)
        assert rep.valid, f"Case {c['case_id']} failed preflight"

    print("All valid cases solved and passed preflight!")

    print(f"Invalid cases to test: {len(invalid_cases)}")
    for c in invalid_cases:
        items = [
            LayoutItemInput(
                node_id=it["node_id"],
                role=it["role"],
                min_width=it["min_width"],
                min_height=it["min_height"],
            )
            for it in c["items"]
        ]
        try:
            solve_layout(c["case_id"], c["strategy"], c["profile"], items)
            raise AssertionError(f"Expected {c['case_id']} to raise LayoutUnsatisfiableError, but it succeeded")
        except LayoutUnsatisfiableError as exc:
            assert exc.code == c["expected_error"]

    print("All invalid cases correctly raised LayoutUnsatisfiableError!")

    valid_path = fixtures_dir / "layout_simple_cases.json"
    with open(valid_path, "w", encoding="utf-8") as f:
        json.dump(valid_cases, f, ensure_ascii=False, indent=2)
    print(f"Saved: {valid_path}")

    invalid_path = fixtures_dir / "layout_invalid_cases.json"
    with open(invalid_path, "w", encoding="utf-8") as f:
        json.dump(invalid_cases, f, ensure_ascii=False, indent=2)
    print(f"Saved: {invalid_path}")


if __name__ == "__main__":
    main()
