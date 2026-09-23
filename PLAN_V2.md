# LearnFlow V2.1 — Complete Architecture Plan

## 0. North Star

LearnFlow V2 không nên trở thành:

```text
Prompt
→ LLM
→ Manim/Python
→ video
```

và cũng không nên là:

```text
Prompt
→ Hermes
→ hàng chục agent
→ video
```

Kiến trúc mục tiêu mình đề xuất là:

```text
                         HERMES
                   Agent Control Plane
                         │
          research / reasoning / pedagogy
             planning / QA / repair
                         │
                         ▼
              PedagogicalStoryboard
                         │
                         ▼
                ┌────────────────┐
                │   SceneGraph   │
                │ Semantic IR    │
                └───────┬────────┘
                        │
                        ▼
                Layout Compiler
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
      Cassowary       ELK          Specialized
       / Kiwi        Layered         Layouts
          │             │              │
          └─────────────┼──────────────┘
                        ▼
                   LayoutGraph
                        │
                        ▼
                 Motion Grammar
                        │
                        ▼
                   MotionPlan
                        │
                        ▼
                   Renderer
                        │
                        ▼
                Deterministic QA
                        │
                 ┌──────┴──────┐
                 │             │
               PASS           FAIL
                 │             │
                 │       deterministic fix
                 │             │
                 │        still failing
                 │             ▼
                 │        VLM Critic
                 │             │
                 │        ScenePatch
                 │             │
                 └──────◄──────┘
                        │
                        ▼
                  final scene
                        │
                        ▼
                 video assembly
                        │
                        ▼
                  video-level QA
                        │
                        ▼
                    final.mp4
```

Nguyên tắc cốt lõi mình muốn giữ rất chặt là:

> **LLM/Hermes quyết định ý nghĩa.  
> SceneGraph biểu diễn ý nghĩa.  
> Layout Engine quyết định vị trí.  
> Motion Grammar quyết định chuyển động hợp lệ.  
> Renderer quyết định pixel.  
> VLM chỉ đánh giá và đề xuất patch — không được tự viết rendering code.**

Nếu phải chọn một điểm khác biệt kỹ thuật lớn nhất của LearnFlow V2, thì chính là ranh giới này.

## 0.1. V2.1 architecture amendments

V2.1 giữ nguyên North Star của V2, nhưng khóa thêm bảy contract để tránh phải rewrite engine sau này:

```text
1. ConceptRegistry ở cấp lesson
   → semantic identity không do từng scene tự phát minh

2. InterSceneTransitionPlan
   → cross-scene continuity là first-class artifact

3. Feasibility-first layout objective
   → hard constraints không được đánh đổi lấy aesthetics

4. Minimal Motion Grammar trước
   → chỉ ship motion verbs chứng minh được giá trị trước khi thêm camera/morph phức tạp

5. Artifact dependency + invalidation graph
   → local repair chỉ rebuild đúng downstream artifacts bị ảnh hưởng

6. VLM quality tier là optional
   → Core deterministic vẫn render/publish được khi VLM unavailable

7. V1/V2 isolation
   → V1 được freeze làm baseline; V2 phát triển side-by-side và chỉ thay default path sau Core Gate
```

Các amendment này không đổi triết lý ban đầu; chúng làm boundary giữa semantics, geometry, motion, repair và orchestration chặt hơn.

---

# 1. Những gì nên học từ các hệ thống mạnh hiện tại

Code2Video dùng Planner → Coder → Critic, lấy executable Manim làm representation chung, rồi dùng VLM Critic với visual anchors để sửa bố cục. Paper còn có ScopeRefine: sửa local trước, chỉ mở rộng phạm vi sửa khi cần. ([showlab.github.io](https://showlab.github.io/Code2Video/?utm_source=chatgpt.com))

Phần mình muốn LearnFlow kế thừa:

```text
✅ structured planning
✅ reproducible rendering
✅ critic feedback
✅ localized repair
✅ parallel scene processing
✅ knowledge-transfer evaluation
```

Nhưng những thứ mình không muốn bê nguyên:

```text
❌ LLM-generated arbitrary Python
❌ LLM-generated x/y coordinates
❌ LLM tự sửa Manim code
❌ VLM trực tiếp kiểm soát pixel placement
```

TheoremExplainAgent cũng cho thấy agentic planning rất quan trọng khi làm video giáo dục dài, nhưng paper vẫn ghi nhận nhiều video còn lỗi nhỏ về bố cục. ([arxiv.org](https://arxiv.org/abs/2502.19400?utm_source=chatgpt.com))

VisualEDU cho thấy một điều còn quan trọng hơn: ngay cả VLM mạnh vẫn gặp khó ở logical correctness, temporal consistency, visual correction và precise tool invocation khi complexity tăng. ([aclanthology.org](https://aclanthology.org/2025.findings-emnlp.889/?utm_source=chatgpt.com))

Vì vậy mình chốt:

> **VLM nên làm critic. Nó không nên làm geometry engine.**

---

# 2. SceneGraph V2 — Semantic Intermediate Representation

SceneGraph phải độc lập hoàn toàn với Pillow, FFmpeg, Manim hay Motion Canvas.

Ví dụ:

```json
{
  "scene_id": "scene_07",
  "purpose": "EXPLAIN",
  "concept": "backpropagation",

  "nodes": [
    {
      "id": "input",
      "kind": "concept",
      "label": "Input",
      "importance": 0.5
    },
    {
      "id": "prediction",
      "kind": "concept",
      "label": "Prediction",
      "importance": 0.7
    },
    {
      "id": "loss",
      "kind": "concept",
      "label": "Loss",
      "importance": 1.0
    }
  ],

  "relations": [
    {
      "source": "input",
      "target": "prediction",
      "kind": "FLOW"
    },
    {
      "source": "prediction",
      "target": "loss",
      "kind": "FLOW"
    }
  ],

  "layout_intent": {
    "type": "PROCESS",
    "reading_direction": "LEFT_TO_RIGHT"
  }
}
```

SceneGraph tuyệt đối không chứa:

```text
x
y
pixel width
absolute font size
FFmpeg expression
Manim function
```

## Node taxonomy

V2 chỉ nên có một tập primitive hữu hạn:

```text
TextNode
MathNode
ConceptNode
ShapeNode
ImageNode
IconNode
ChartNode
CodeNode
GroupNode
ContainerNode
CalloutNode
EquationNode
```

Mình không muốn tạo hàng chục node riêng cho từng domain.

Domain semantics nên đi qua metadata:

```json
{
  "kind": "concept",
  "semantic_role": "LOSS_FUNCTION"
}
```

thay vì:

```text
LossFunctionSpecialNode
```

Như vậy core vẫn general-purpose.

---

# 3. Stable semantic identity

Một feature mình xem là rất đáng làm sớm là:

```text
semantic_key
```

Ví dụ scene 4:

```json
{
  "id": "loss_scene4",
  "semantic_key": "concept:loss"
}
```

scene 5:

```json
{
  "id": "loss_scene5",
  "semantic_key": "concept:loss"
}
```

Engine hiểu đây là cùng một khái niệm.

Nhờ đó ta có thể làm:

```text
scene 4
LOSS ở giữa màn hình
     ↓

scene transition
     ↓

scene 5
LOSS dịch sang bên trái
```

thay vì:

```text
fade out
fade in object mới
```

Từ một `semantic_key` ổn định, ta có thể xây:

```text
object persistence
semantic morph
layout continuity
camera continuity
```

Đây là một trong những thứ sẽ khiến video bớt cảm giác slideshow rất nhiều.

## 3.1. ConceptRegistry — canonical semantic identity ở cấp lesson

`semantic_key` không nên do từng scene hoặc Visual Director tự phát minh độc lập.

Trước khi SceneGraph được tạo, storyboard compiler nên xây một `ConceptRegistry` cho toàn lesson:

```json
{
  "concepts": [
    {
      "concept_id": "c_loss",
      "canonical_key": "concept:loss",
      "label": "Loss",
      "aliases": ["loss function", "error function"],
      "semantic_type": "CONCEPT"
    }
  ]
}
```

Mỗi SceneGraph node chỉ reference canonical identity:

```json
{
  "id": "loss_scene4",
  "concept_ref": "c_loss",
  "semantic_key": "concept:loss"
}
```

Invariant:

```text
Scene-local node id
!=
lesson-wide semantic identity
```

`ConceptRegistry` chịu trách nhiệm:

```text
canonical concept IDs
alias normalization
semantic-key uniqueness
cross-scene concept matching
concept provenance
optional domain metadata
```

Nhờ vậy continuity không phụ thuộc model có viết đúng cùng một string ở nhiều scene hay không.

Nếu một scene reference concept không có trong registry:

```text
SCENEGRAPH_UNKNOWN_CONCEPT_REF
```

Nếu hai concepts cố dùng cùng canonical key nhưng khác nghĩa:

```text
CONCEPT_REGISTRY_COLLISION
```

ConceptRegistry phải versioned và serialize ổn định vì nó là input cho layout continuity, transition planning, repair và benchmark replay.

---

# 4. SceneGraph relation taxonomy

SceneGraph không nên chỉ có edge kiểu graph thông thường.

Relations nên gồm:

```text
FLOW
CAUSES
DEPENDS_ON
COMPARES_WITH
CONTRASTS_WITH
PART_OF
GROUP_WITH
LABELS
ANNOTATES
TRANSFORMS_INTO
EQUIVALENT_TO
SEQUENCE_BEFORE
SEQUENCE_AFTER
```

Lợi ích là Layout Engine có thể dùng luôn semantics.

Ví dụ:

```text
COMPARES_WITH
```

→ ưu tiên symmetric two-column.

```text
CAUSES
```

→ ưu tiên directional causal graph.

```text
PART_OF
```

→ ưu tiên nested container.

Tức là layout không chỉ hiểu topology, mà còn hiểu loại quan hệ.

---

# 5. LayoutHint — LLM được gợi ý nhưng không được đặt pixel

Ta vẫn cho model truyền intent:

```json
{
  "layout_hint": {
    "preferred_region": "LEFT",
    "importance": 0.8,
    "keep_near": ["loss"],
    "keep_apart": ["target"],
    "preferred_order": 2
  }
}
```

Nhưng không bao giờ cho:

```json
"x": 472,
"y": 253
```

Model có thể nói:

> “loss nên ở trung tâm.”

Nhưng Layout Engine mới là thành phần quyết định trung tâm đó chính xác ở đâu.

---

# 6. SceneGraph Compiler

Pipeline compile nên rõ từng phase:

```text
SceneGraph
   ↓
Schema validation
   ↓
Semantic normalization
   ↓
Intrinsic measurement
   ↓
Topology classification
   ↓
Layout strategy selection
   ↓
Constraint generation
   ↓
Layout solving
   ↓
Edge routing
   ↓
Collision pass
   ↓
Typography fitting
   ↓
Visual balance pass
   ↓
LayoutGraph
```

Mỗi stage nên tạo report riêng.

Nếu fail:

```text
SceneGraphCompilerError
```

phải chỉ ra lỗi xảy ra ở phase nào, chứ không trả một “render failed” chung chung.

---

# 7. Intrinsic Measurement Engine

Trước khi layout, engine phải biết kích thước thật.

Ví dụ:

```text
"Loss"
```

và:

```text
"Backpropagation updates every parameter"
```

rõ ràng không thể được xem như hai node cùng kích thước.

Measurement engine cần tính:

```text
text bbox
wrapped text bbox
math bbox
image aspect ratio
icon bbox
minimum readable width
minimum readable height
```

Typography phải được đo trước constraint solving, không sửa font sau khi mọi thứ đã nằm cố định.

---

# 8. Layout Engine không dùng một thuật toán duy nhất

Mình sẽ không cố ép mọi scene vào một solver.

## LayoutRouter

```text
Scene topology
     ↓
LayoutRouter
     │
     ├─ comparison/card/list
     │       → ConstraintLayout
     │
     ├─ process/DAG
     │       → ELK Layered
     │
     ├─ tree
     │       → layered/tree layout
     │
     ├─ undirected relationship
     │       → force-directed
     │
     ├─ timeline
     │       → TimelineLayout
     │
     ├─ equation
     │       → EquationLayout
     │
     └─ chart
             → ChartLayout
```

ELK Layered rất hợp với flow/DAG vì bản thân nó đã có các phase cycle breaking, layering, crossing minimization, node placement và edge routing; ngoài ra còn hỗ trợ orthogonal/spline routing, ports và compound graphs. ([eclipse.dev](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html?utm_source=chatgpt.com))

Graphviz `dot` cũng được thiết kế cho directed hierarchical graph, với mục tiêu giảm crossings và edge length. ([graphviz.org](https://graphviz.org/docs/layouts/dot/?utm_source=chatgpt.com))

---

# 9. Constraint Layout bằng Kiwi/Cassowary

Cho những scene kiểu UI hoặc card, mình sẽ dùng:

```text
kiwisolver
```

đặc biệt cho:

```text
cards
comparisons
titles
image + text
quote
callout
multi-column
```

Kiwi là implementation C++ hiệu quả của Cassowary và có Python bindings. ([kiwisolver.readthedocs.io](https://kiwisolver.readthedocs.io/en/latest/?utm_source=chatgpt.com))

Constraints có thể là:

```text
title.left >= safe_left

title.right <= safe_right

diagram.top >= title.bottom + GAP_L

diagram.bottom <= subtitle_safe_top

left.width == right.width

left.center_y == right.center_y
```

Và nên có strength:

```text
REQUIRED
STRONG
MEDIUM
WEAK
```

Ví dụ:

```text
REQUIRED:
within_safe_area

STRONG:
symmetry

MEDIUM:
preferred_region

WEAK:
stay_near_previous_position
```

Kiwi hỗ trợ constraints với strength khác nhau. ([kiwisolver.readthedocs.io](https://kiwisolver.readthedocs.io/en/latest/basis/index.html?utm_source=chatgpt.com))

---

# 10. Collision solving không nên giao hoàn toàn cho Cassowary

Đây là một chi tiết implementation quan trọng.

Constraint:

```text
A không overlap B
```

thực chất là disjunctive:

```text
A left of B
OR
A right of B
OR
A above B
OR
A below B
```

nên không phải một linear constraint đơn giản.

Pipeline hợp lý hơn là:

```text
Cassowary solve
      ↓
collision detection
      ↓
choose separation axis
      ↓
add temporary inequality
      ↓
solve again
```

Lặp tối đa N lần.

Nếu vẫn không thỏa:

```text
layout strategy escalation
```

Ví dụ đổi từ horizontal sang two-row layout.

---

# 11. Layout scoring function — feasibility trước, aesthetics sau

Không dùng một weighted sum duy nhất để cho phép một layout “đẹp hơn” bù cho clipping hoặc fatal overlap.

Layout evaluation chia thành hai tầng.

## Stage A — hard feasibility gate

Candidate chỉ được đi tiếp khi:

```text
overflow == 0
fatal_overlap == 0
clipping == 0
edge_node_intersection == 0
minimum_font_size satisfied
safe_zone satisfied
invalid_geometry == 0
```

Một candidate fail hard constraint bị loại, không được giữ lại bằng cách giảm các penalty khác.

## Stage B — rank feasible candidates

Chỉ trên tập candidate đã feasible mới tính soft objective:

\[
J_{soft} =
\lambda_e E +
\lambda_t T +
\lambda_b B +
\lambda_d D +
\lambda_w W
\]

Trong đó:

```text
E = edge crossing / edge length penalty
T = typography preference penalty trong readability-safe range
B = visual imbalance
D = displacement from previous scene
W = whitespace / density penalty
```

Mình đặc biệt muốn giữ `D`.

Nếu `"loss"` đang nằm bên phải ở scene trước, scene sau không nên ngẫu nhiên bay lên top-left nếu không có lý do.

Rule:

```text
hard correctness > continuity > readability preference > aesthetics
```

Nếu không có candidate feasible:

```text
strategy escalation
→ reflow
→ alternate topology layout
→ split content
→ LAYOUT_UNSATISFIABLE
```

---

# 12. Continuity-aware layout

Layout mới nhận thêm:

```text
previous_layout
```

và chuyển vị trí cũ thành soft constraints:

```text
x_new ≈ x_old
y_new ≈ y_old
```

Kiwi không còn stay constraints nguyên bản như Cassowary cũ, nhưng có thể mô phỏng bằng weak constraints/edit variables. ([kiwisolver.readthedocs.io](https://kiwisolver.readthedocs.io/en/latest/basis/solver_internals.html?utm_source=chatgpt.com))

Đối với ELK, ta có thể dùng ordering/interactive constraints để tăng độ ổn định giữa các lần layout. ([eclipse.dev](https://eclipse.dev/elk/blog/posts/2023/23-01-09-constraining-the-model.html?utm_source=chatgpt.com))

---

# 13. Safe Region System

Mỗi aspect ratio nên có:

```text
FrameProfile
```

Ví dụ 16:9:

```text
SAFE_TITLE
SAFE_CONTENT
SAFE_CAPTION
SAFE_EDGE
```

9:16:

```text
TOP_HOOK
PRIMARY_CONTENT
SUBTITLE_ZONE
BOTTOM_UI_SAFE
```

Renderer không được tự đặt object ra ngoài các vùng này trừ khi có explicit override.

---

# 14. Adaptive typography

Typography engine tự quyết định:

```text
font size
wrap width
line count
tracking
line height
```

dựa trên:

```text
node importance
available area
word count
visual hierarchy
```

Rule nên theo thứ tự:

```text
measure at preferred size
    ↓
wrap
    ↓
reflow layout
    ↓
shrink within readability-safe range
    ↓
split content
```

Không làm kiểu:

```text
shrink font liên tục cho tới khi vừa
```

Typography shrink chỉ là một late-stage optimization trong một khoảng font size an toàn; nó không được dùng để che một layout strategy kém.

Nếu xuống dưới readability threshold:

```text
LAYOUT_UNSATISFIABLE
```

để upstream chia lại scene.

---

# 15. Edge routing

Flow diagrams cần một subsystem riêng cho:

```text
ports
orthogonal routing
arrowhead clearance
edge-label clearance
node-edge intersection check
```

ELK hỗ trợ port constraints và orthogonal routing, rất hợp cho block/process diagrams. ([eclipse.dev](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html?utm_source=chatgpt.com))

SceneGraph chỉ cần khai báo:

```json
{
  "source_port": "AUTO",
  "target_port": "AUTO"
}
```

không cho LLM chọn tọa độ.

---

# 16. LayoutPreflight

Trước khi render:

```text
overflow == 0
clipping == 0
fatal_overlap == 0
edge_node_intersection == 0
min_font_size satisfied
safe_zone satisfied
aspect_ratio distortion <= threshold
```

Nếu fail:

```text
không render.
```

Ta sửa ở layout layer trước khi tốn công render.

---

# 17. Motion Grammar — semantic animation DSL

Motion phải tách khỏi layout.

SceneGraph không chứa animation code.

Tạo:

```text
MotionPlan
```

Ví dụ:

```json
{
  "events": [
    {
      "id": "e1",
      "target": "prediction",
      "verb": "ENTER",
      "trigger": {
        "beat": "prediction_phrase"
      },
      "style": "FADE_UP"
    },
    {
      "id": "e2",
      "target": "loss",
      "verb": "EMPHASIZE",
      "trigger": {
        "beat": "error_phrase"
      },
      "style": "PULSE"
    }
  ]
}
```

---

# 18. Motion verb taxonomy

Mình sẽ giữ grammar nhỏ và có kiểm soát.

## ENTER

```text
FADE
SLIDE
SCALE_IN
DRAW
REVEAL
```

## EMPHASIZE

```text
PULSE
HIGHLIGHT
GLOW
UNDERLINE
FOCUS
```

## TRANSFORM

```text
MOVE
RESIZE
MORPH
REPLACE
```

## RELATION

```text
DRAW_EDGE
TRACE_PATH
PROPAGATE
```

## CAMERA

```text
PUSH
PAN
FOCUS_REGION
RESET
```

## EXIT

```text
FADE
SLIDE
COLLAPSE
```

LLM không được tạo thêm verb ngoài enum.

## 18.1. Motion Grammar phải ship theo capability tiers

Không implement toàn bộ taxonomy trong checkpoint đầu.

### Motion Tier 1 — bắt buộc cho V2B đầu tiên

```text
ENTER:
  FADE
  SLIDE
  REVEAL

EMPHASIZE:
  HIGHLIGHT
  PULSE
  FOCUS

RELATION:
  DRAW_EDGE
  PROPAGATE

TRANSFORM:
  MOVE

EXIT:
  FADE
```

Tier 1 phải chứng minh được:

```text
narration alignment tốt hơn V1
không tăng motion conflict
không làm giảm readability
replay deterministic
```

### Motion Tier 2 — chỉ mở sau benchmark gate

```text
RESIZE
MORPH
TRACE_PATH
UNDERLINE
SCALE_IN
COLLAPSE
```

### Motion Tier 3 — deferred

```text
CAMERA PUSH
PAN
FOCUS_REGION
RESET
complex cross-scene morph
```

Camera và morph là high-complexity features; không được trở thành dependency của basic V2 motion.

---

# 19. Motion compiler

Motion DSL:

```text
semantic event
      ↓
motion compiler
      ↓
property tracks
```

Ví dụ:

```text
ENTER + FADE_UP
```

compile thành:

```text
opacity: 0 → 1
y-offset: +24 → 0
duration: 420 ms
easing: ease-out
```

LLM không cần biết các chi tiết này.

Motion Canvas cũng dùng abstraction signal/tween để thay đổi property theo thời gian; LearnFlow có thể học cách tách state khỏi animation như vậy mà không cần phụ thuộc Motion Canvas ngay lập tức. ([motion-canvas.io](https://motion-canvas.io/docs/signals/?utm_source=chatgpt.com))

---

# 20. Semantic Beats

Timing nên bám narration.

Pipeline:

```text
TTS
 ↓
word timestamps
 ↓
phrase timestamps
 ↓
semantic beat extraction
 ↓
MotionPlan binding
```

Ví dụ narration:

```text
"The model makes a prediction,
compares it with the target,
and propagates the error backward."
```

Beat map:

```text
0.0 prediction
2.1 target comparison
4.8 error
5.5 backward propagation
```

Motion:

```text
0.2  prediction ENTER
2.2  target ENTER
2.7  comparison HIGHLIGHT
4.8  loss PULSE
5.5  backward edges PROPAGATE
```

Đây là thứ khiến animation có cảm giác phục vụ lời giảng thay vì chạy độc lập.

---

# 21. Motion Scheduler

Motion events tạo thành dependency DAG:

```text
e1 ENTER prediction
       ↓
e2 ENTER target
       ↓
e3 COMPARE
       ↓
e4 PROPAGATE
```

Scheduler phải kiểm:

```text
event conflict
target availability
duration
scene boundary
camera conflict
simultaneous motion count
```

Ví dụ:

```text
EXIT(node)
```

không được chạy trước:

```text
EMPHASIZE(node)
```

---

# 22. Motion cognitive budget

Không phải càng nhiều animation càng tốt.

Default có thể là:

```text
max_major_simultaneous_motion = 2
max_minor_simultaneous_motion = 3
```

Dense narration:

```text
less motion
```

Pause / transition:

```text
more motion allowed
```

Mục tiêu là tránh kiểu PowerPoint “mọi thứ đều bay”.

---

# 23. Persistent-object transitions

Nếu:

```text
semantic_key(scene4.node)
==
semantic_key(scene5.node)
```

Motion planner có thể tự sinh:

```text
MOVE
RESIZE
MORPH
```

thay vì:

```text
EXIT
ENTER
```

Ví dụ:

```text
Scene 4
Input → Model → Prediction

Scene 5
             Prediction
                  ↓
                 Loss
```

`Prediction` thật sự di chuyển sang vị trí mới.

Đây là một feature mình đánh giá rất cao vì nó vừa tăng polish vừa tăng continuity.

## 23.1. InterSceneTransitionPlan là first-class artifact

Cross-scene motion không thuộc hoàn toàn scene trước hay scene sau, nên không được nhét ngầm vào `MotionPlan` của một scene.

Tạo contract riêng:

```json
{
  "transition_id": "scene_04__scene_05",
  "from_scene": "scene_04",
  "to_scene": "scene_05",
  "persistent_objects": [
    {
      "semantic_key": "concept:prediction",
      "operation": "MOVE",
      "from_node": "prediction_scene4",
      "to_node": "prediction_scene5"
    }
  ],
  "duration_ms": 500
}
```

Compiler input:

```text
previous LayoutGraph
+ next LayoutGraph
+ ConceptRegistry
+ continuity policy
→ InterSceneTransitionPlan
```

Renderer protocol vì vậy nên tách:

```python
class RendererBackend:
    render_scene(layout_graph, motion_plan, assets) -> RenderedScene
    render_transition(transition_plan, prev_frame, next_layout, assets) -> RenderedTransition
```

Không backend nào bị bắt buộc phải support Tier-2/Tier-3 transition ngay.

Capability negotiation:

```text
backend supports MOVE transition
→ render persistent move

backend does not support it
→ deterministic FADE_OUT / FADE_IN fallback
```

Invariant:

```text
unsupported transition
!=
render failure
```

V2-10 chỉ được coi hoàn chỉnh khi transition artifact có schema/versioning/test riêng, không chỉ là logic ad-hoc trong assembler.

---

# 24. Renderer adapter

V2 không nên khóa vào một renderer.

Interface:

```python
class RendererBackend:
    render(layout_graph, motion_plan, assets) -> RenderedScene
```

Backends:

```text
PillowFFmpegRenderer
ManimRenderer
MotionCanvasRenderer      # optional later
```

Tất cả cùng nhận:

```text
LayoutGraph + MotionPlan
```

Không nhận raw prompt.

---

# 25. Deterministic QA phải chạy trước VLM

VLM đắt hơn và không deterministic.

Pipeline:

```text
render
 ↓
DeterministicAnalyzer
 ↓
PASS?
```

Check:

```text
clipping
overflow
bbox overlap
edge-node intersection
minimum font size
invalid alpha
missing asset
unexpected black frame
audio silence
duration mismatch
subtitle bounds
```

Chỉ khi deterministic pass nhưng chất lượng vẫn có thể kém mới gọi VLM.

## 25.1. QualityMode — VLM là quality tier optional

Core V2 phải có hai mode rõ ràng:

```text
quality_mode=deterministic
quality_mode=critic
```

### deterministic

```text
render
→ deterministic QA
→ PASS
→ publish candidate
```

Không gọi VLM. Đây là mode bắt buộc phải chạy offline khỏi critic provider.

### critic

```text
render
→ deterministic QA
→ PASS
→ VLM Critic
→ optional patch/repair
→ deterministic re-check
→ publish
```

Nếu VLM unavailable, timeout, quota exhausted hoặc provider lỗi:

```text
deterministic gate PASS
→ emit critic_unavailable warning
→ continue with deterministic-approved artifact
```

Trừ khi deployment policy explicit yêu cầu strict critic mode.

Không được để VLM outage phá khả năng render cơ bản của LearnFlow Core.

VLM output không bao giờ bypass deterministic re-check sau repair.

---

# 26. VLM Critic input

Critic không chỉ nhìn screenshot.

Input nên gồm:

```text
1. narration
2. SceneGraph
3. LayoutGraph summary
4. MotionPlan
5. rendered keyframes
6. element ID overlay
7. anchor grid overlay
8. deterministic QA report
```

Keyframes lấy theo events:

```text
scene start
after major ENTER
after major TRANSFORM
before exit
scene end
```

Không sample random.

---

# 27. Visual Anchor Layer

Code2Video discretizes canvas thành 6×6 grid để critic không phải đưa feedback mơ hồ như “dịch sang trái một chút”. ([alphaxiv.org](https://www.alphaxiv.org/abs/2510.01174v1?utm_source=chatgpt.com))

LearnFlow nên mở rộng thành:

```text
semantic regions
+
anchor grid
+
element IDs
```

Frame critic thấy:

```text
[A01][A02][A03]...
```

và:

```text
#loss
#prediction
#target
```

Critic có thể nói:

```text
move #loss toward CENTER_RIGHT
```

nhưng không được nói:

```text
set x=583
```

---

# 28. Structured Critic output

Mình sẽ không nhận prose tự do.

```json
{
  "status": "REPAIR",

  "issues": [
    {
      "type": "VISUAL_HIERARCHY",
      "severity": "MEDIUM",
      "targets": ["loss"],
      "reason": "The key concept is visually weaker than supporting nodes."
    }
  ],

  "patches": [
    {
      "op": "INCREASE_IMPORTANCE",
      "target": "loss",
      "value": 0.15
    }
  ]
}
```

JSON Schema phải được enforce.

openai/gpt-6-luna hiện nhận image input, hỗ trợ tools và structured JSON output; với mức giá tham khảo OpenRouter khoảng $0.10/M input và $0.50/M output, đủ rẻ và nhanh để làm critic mặc định trong development.

---

# 29. Patch DSL

Critic chỉ được phép gọi whitelist:

```text
SET_REGION
CHANGE_LAYOUT_STRATEGY
INCREASE_GAP
DECREASE_GAP
CHANGE_IMPORTANCE
SCALE_NODE
REWRAP_TEXT
SPLIT_GROUP
MERGE_GROUP
REROUTE_EDGE
CHANGE_EDGE_STYLE
CHANGE_VISUAL_INTENT
REMOVE_DECORATION
ADD_EMPHASIS
CHANGE_MOTION_STYLE
REDUCE_MOTION
```

Không có:

```text
EXECUTE_CODE
SET_PIXEL
WRITE_PYTHON
FFMPEG_COMMAND
```

---

# 30. Scene repair dùng ScopeRefine ở graph level

Mình muốn lấy tinh thần ScopeRefine của Code2Video, nhưng chuyển nó từ code scope sang semantic scope. ([alphaxiv.org](https://www.alphaxiv.org/abs/2510.01174v1?utm_source=chatgpt.com))

```text
LEVEL 0
deterministic auto-fix

LEVEL 1
single-node patch

LEVEL 2
group/layout patch

LEVEL 3
recompile entire SceneGraph

LEVEL 4
Visual Director regenerate scene

LEVEL 5
deterministic fallback
```

Ví dụ:

```text
text clipping
```

→ Level 0.

```text
two nodes visually confusing
```

→ Level 1.

```text
whole process diagram overcrowded
```

→ Level 2.

```text
wrong visual metaphor
```

→ Level 4.

## 30.1. Artifact dependency graph + deterministic invalidation

Selective repair chỉ đáng tin nếu engine biết artifact downstream nào trở nên stale sau một patch.

Mỗi artifact nên có:

```text
schema_version
content_hash
input_hashes[]
created_by_phase
scene_id / transition_id
```

Dependency chain điển hình:

```text
ConceptRegistry
      ↓
SceneGraph
      ↓
LayoutGraph
      ↓
MotionPlan
      ↓
RenderedScene
      ↓
Scene QA
      ↓
Assembly
      ↓
Video QA
```

Transition path:

```text
LayoutGraph(scene_n)
+ LayoutGraph(scene_n+1)
+ ConceptRegistry
      ↓
InterSceneTransitionPlan
      ↓
RenderedTransition
```

Invalidation rules phải explicit. Ví dụ:

```text
Patch SceneGraph geometry semantics
→ invalidate LayoutGraph
→ MotionPlan if target availability/order changed
→ RenderedScene
→ Scene QA
→ affected transitions
→ final assembly

Change only style token
→ keep SceneGraph/LayoutGraph
→ invalidate render + QA + assembly

Change narration text
→ invalidate TTS / beats / MotionPlan timing
→ render if motion timing changes
→ assembly

Change one layout hint
→ invalidate layout downstream only for that scene
```

Không được resynthesize narration nếu patch chỉ sửa geometry.

Không được rerender scene khác nếu dependency graph chứng minh chúng unchanged.

Hash equality cho phép cache reuse an toàn:

```text
inputs unchanged
+ compiler version unchanged
→ artifact reusable
```

Đây là contract bắt buộc cho claim:

> “sửa một scene không render lại cả lesson.”

---

# 31. Hard repair limits

```text
MAX_LAYOUT_SOLVES = 5
MAX_VLM_REPAIR_ROUNDS = 2
MAX_SCENE_REGENERATIONS = 1
```

Nếu vẫn fail:

```text
fallback renderer
```

Ví dụ:

```text
complex graph fails
 ↓
simplify graph
 ↓
still fails
 ↓
concept card + sequential reveal
```

Một bài học nên ưu tiên hoàn thành được hơn là kẹt vô hạn ở một scene.

---

# 32. Scene quality score

Mỗi scene có:

```text
Q_scene =
  w1 structural
+ w2 readability
+ w3 semantic_alignment
+ w4 pedagogy
+ w5 aesthetics
+ w6 temporal_clarity
```

Structural/readability nên deterministic càng nhiều càng tốt.

Semantic/pedagogy/aesthetics mới dùng VLM.

Không để VLM chấm tất cả mọi thứ.

---

# 33. Video-level critic

Sau khi từng scene pass:

```text
final draft
 ↓
VideoCritic
```

Check:

```text
visual repetition
scene rhythm
style consistency
transition continuity
concept progression
pacing
narration redundancy
visual modality diversity
```

Ví dụ:

```text
scene 2 = diagram
scene 3 = diagram
scene 4 = diagram
scene 5 = diagram
scene 6 = diagram
```

Video critic có thể trả:

```text
scene 4 → illustration
scene 6 → comparison
```

PIVOT nhấn mạnh rằng educational-video generation cần cả pedagogical structure lẫn multimodal verification, không chỉ visual coherence. ([arxiv.org](https://arxiv.org/abs/2609.24083?utm_source=chatgpt.com))

---

# 34. V2 vẫn phải chạy được khi không có Hermes

Đây là requirement bắt buộc.

```text
LearnFlow Core V2
```

cần có API:

```text
POST /compile
POST /render
POST /verify
POST /repair
```

và có thể chạy:

```text
Storyboard JSON
→ final.mp4
```

hoàn toàn không cần Hermes.

Nếu Hermes lỗi:

```text
engine vẫn chạy.
```

Điều này giữ LearnFlow là một sản phẩm độc lập thay vì một plugin phụ thuộc agent runtime.

---

# 35. Chỉ sau khi Core V2 đạt gate mới gắn Hermes

Kiến trúc:

```text
             ┌────────────────────┐
             │ Hermes AIAgent     │
             │ Lesson Director    │
             └─────────┬──────────┘
                       │
              reasoning / tools
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
 Research        Pedagogy          Fact Check
      │                │                │
      └────────────────┼────────────────┘
                       ▼
                 LessonPlan
                       ↓
                   Script
                       ↓
              Visual Director
                       ↓
                 SceneGraph[]
                       ↓
           ┌──────────────────────┐
           │ LearnFlow Core V2    │
           │                      │
           │ Layout               │
           │ Motion               │
           │ Render               │
           │ Verify               │
           │ Repair               │
           └───────────┬──────────┘
                       ↓
                   final.mp4
```

Hermes lúc này không thay renderer. Nó chỉ điều phối những quyết định cấp cao.

---

# 36. Hermes không nên bị fork sâu

Mình sẽ dùng upstream Hermes + một LearnFlow project plugin.

Hermes hiện hỗ trợ project plugins, custom tools, hooks, skills và model providers. Plugin có thể intercept `pre_tool_call`, quan sát `post_tool_call`, inject context và theo dõi subagent lifecycle. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/plugins/index.md?utm_source=chatgpt.com))

Structure:

```text
learnflow/
│
├── app/
├── scenegraph/
├── layout/
├── motion/
├── rendering/
├── verification/
├── agent_contracts/
│
├── AGENTS.md
│
└── .hermes/
    └── plugins/
        └── learnflow/
            ├── plugin.yaml
            ├── plugin.py
            └── skills/
```

Hermes project plugins có thể nằm trong `.hermes/plugins/` khi project plugin discovery được bật. ([github.com](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/features/built-in-plugins.md?utm_source=chatgpt.com))

---

# 37. Hermes constitution

`AGENTS.md` nên chứa các invariant:

```text
LEARNFLOW CONSTITUTION

1. Never generate executable rendering code.
2. Never manually assign pixel positions.
3. All visuals must compile through SceneGraph.
4. Never bypass SceneGraph validation.
5. Never bypass QualityGate.
6. Never publish an unverified artifact.
7. Prefer deterministic repair before VLM repair.
8. Prefer local repair over scene regeneration.
9. Never regenerate the whole lesson to fix one scene.
10. Never exceed BudgetLedger.
11. Research claims require provenance.
12. final.mp4 is published only by LearnFlow Core.
```

Hermes đọc project-specific instructions như `AGENTS.md`, nên đây là nơi phù hợp để giữ các rule ổn định. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/tips.md?utm_source=chatgpt.com))

---

# 38. Hermes tool boundary

Không expose:

```text
terminal
raw FFmpeg
renderer internals
file paths
Pillow primitives
Manim internals
```

cho production agent.

Chỉ expose capability-level tools:

```text
learnflow_create_run

learnflow_store_research

learnflow_validate_lesson

learnflow_validate_scenegraph

learnflow_compile_scene

learnflow_render_scene

learnflow_verify_scene

learnflow_apply_scene_patch

learnflow_render_lesson

learnflow_get_run_status

learnflow_get_budget

learnflow_publish
```

Hermes dùng LearnFlow như một production service có contract rõ.

---

# 39. Parent agent — Lesson Director

Input:

```text
user query
learner level
target length
language
style
budget
```

Director tự quyết:

```text
do we need research?
how deep?
which specialists?
what learning objectives?
what needs verification?
```

Không phải query nào cũng spawn một swarm lớn.

---

# 40. Research Orchestrator

Hermes `delegate_task` tạo subagents với context riêng; chỉ final summary đi về parent, nên context của parent không bị lấp bởi tool trace. Nested delegation là opt-in. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md?utm_source=chatgpt.com))

Cây mình muốn:

```text
Lesson Director
      │
      └── Research Orchestrator
              │
       ┌──────┼────────┐
       ▼      ▼        ▼
   Concept Evidence Misconception
   Research Research   Research
```

Depth:

```text
2
```

là đủ cho hầu hết lesson.

---

# 41. Không dùng subagent cho mechanical work

Hermes phân biệt rất rõ:

```text
delegate_task
→ reasoning / judgment

execute_code
→ mechanical processing
```

([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md?utm_source=chatgpt.com))

Ví dụ:

```text
search 20 queries
deduplicate URLs
group citations
calculate scores
```

→ `execute_code`.

Nhưng:

```text
Which explanation is pedagogically better?
```

→ subagent.

Cách này vừa rẻ hơn vừa giữ agent tree gọn.

---

# 42. ResearchPack

Research output không nên chỉ là vài đoạn markdown.

```json
{
  "topic": "...",

  "concepts": [],

  "claims": [
    {
      "claim_id": "C001",
      "statement": "...",
      "sources": [],
      "confidence": 0.95
    }
  ],

  "misconceptions": [],

  "examples": [],

  "open_questions": []
}
```

Từ đó build:

```text
EvidenceGraph
```

---

# 43. EvidenceGraph

```text
Source A ──┐
           ├── C001
Source B ──┘

Source C ───── C002

C001 + C002 ── C003
```

Narration gắn claim IDs:

```json
{
  "text": "Self-attention...",
  "claims": ["C001", "C003"]
}
```

Fact Checker nhìn vào đây có thể phát hiện:

```text
claim trong script
nhưng không có evidence
```

→ `UNSUPPORTED_CLAIM`.

Đây là cách tốt hơn nhiều so với “fact-check toàn bài” bằng một prompt mơ hồ.

---

# 44. Pedagogy Agent

Pedagogy Agent chưa viết narration.

Output:

```text
learning objectives
prerequisites
concept order
worked examples
analogies
misconceptions
assessment probes
```

Pipeline nên rất rõ:

```text
Research
  ↓
what is true

Pedagogy
  ↓
how to teach it

Script
  ↓
how to say it

Visual Director
  ↓
how to show it
```

PIVOT đi theo đúng hướng đưa instructional principles vào storyboard trước, rồi verification và misconception-aware remediation sau. ([arxiv.org](https://arxiv.org/abs/2609.24083?utm_source=chatgpt.com))

---

# 45. Script Agent

Output:

```json
{
  "segment_id": "s5",

  "narration": "...",

  "claims": [
    "C013"
  ],

  "teaching_function": "DEMONSTRATE",

  "emphasis": [
    "gradient"
  ]
}
```

Script Agent không output visual code.

---

# 46. Visual Director

Visual Director là agent trực tiếp tạo:

```text
SceneGraph
```

nhưng chỉ ở mức semantic structure.

Nó nhìn toàn lesson để tối ưu:

```text
visual rhythm
visual diversity
concept continuity
cognitive load
style consistency
```

Ví dụ chuỗi scene:

```text
ILLUSTRATION
→ PROCESS
→ WORKED_EXAMPLE
→ COMPARISON
→ EQUATION
→ ILLUSTRATION
```

sẽ tốt hơn 6 diagram nối tiếp nhau.

---

# 47. Hermes tool safety

Một chi tiết khá quan trọng: delegated Hermes agents kế thừa enabled toolsets của parent, nên root production profile không nên được cấp raw tools quá rộng. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/delegation.md?utm_source=chatgpt.com))

Production profile chỉ nên có:

```text
research web tools
LearnFlow plugin tools
structured artifact tools
safe execute_code capabilities
```

Không:

```text
arbitrary local rendering mutation
```

Nếu sau này cần role isolation mạnh hơn nữa, chuyển sang Kanban worker profiles.

---

# 48. Hermes Hooks

`pre_tool_call`:

```text
validate state
validate budget
validate tool permissions
validate SceneGraph version
```

Hermes plugin hooks có thể block tool call trước khi nó chạy. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/plugins/index.md?utm_source=chatgpt.com))

`post_tool_call`:

```text
record:
model
tokens
cost
duration
artifact
scene_id
agent_id
```

`subagent_start/stop`:

```text
record agent provenance
```

Như vậy toàn bộ orchestration có audit trail.

---

# 49. BudgetLedger

Budget cần là first-class object:

```json
{
  "max_usd": 1.00,

  "spent": {
    "llm": 0.10,
    "vlm": 0.03,
    "image": 0.05,
    "tts": 0.00
  },

  "remaining": 0.82,

  "limits": {
    "subagent_calls": 12,
    "vlm_repairs": 8,
    "image_generations": 10
  }
}
```

Nếu budget xuống thấp:

```text
generative illustration
↓
deterministic visual
```

Không làm fail cả lesson.

---

# 50. Model strategy

Ở giai đoạn đầu, mình sẽ cố tình đơn giản:

```text
Director
Research
Pedagogy
Script
Visual Director
VLM critic

→ openai/gpt-6-luna
```

Không phải vì Luna luôn tốt nhất cho mọi role, mà vì hiện tại nó rẻ, nhận text/image/PDF, hỗ trợ tools + structured output và có context lớn.

Khi pipeline đã ổn định mới tối ưu model theo từng role.

## Model / Provider Strategy Amendment — 2026-09-23

### A1. OpenRouter-First Gateway
- LearnFlow V2 chuyển sang kiến trúc **OpenRouter-first** cho toàn bộ AI model inference.
- Primary production credential duy nhất: `OPENROUTER_API_KEY`.
- Mục tiêu kiến trúc: **một billing account, một model gateway, phục vụ đa dạng capabilities** (reasoning/agents, vision critic, image generation, TTS, speech-to-text, embeddings, reranking).
- **Phân tách domain interfaces**: Không xây dựng một `OpenRouterEverythingProvider` monolithic duy nhất. Các domain abstractions độc lập hoàn toàn với billing gateway:
  - `ReasoningProvider`
  - `ImageProvider`
  - `SpeechProvider`
  - `TranscriptionProvider`
  - `EmbeddingProvider`
  - `RerankProvider`
  Mỗi interface có adapter riêng kết nối tới OpenRouter endpoint tương ứng. Provider abstraction độc lập với billing gateway.

### A2. Authoritative Agent & Critic Model: `openai/gpt-6-luna`
- Toàn bộ vai trò nòng cốt (`Director`, `Research`, `Pedagogy`, `Script`, `Visual Director`, `VLM Critic`) sử dụng mặc định: `openai/gpt-6-luna`.
- Đối với các case phức tạp: ưu tiên tăng reasoning effort trước khi leo thang sang họ model khác. Không đặt GPT-6 Sol làm mặc định thường trực.
- Lý do chọn Luna: chi phí cực thấp, context lớn, nhận multimodal vision/PDF/file, hỗ trợ tool calling và JSON structured output tin cậy cho agent loops tốc độ cao.
- Mức giá tham khảo (tháng 09/2026, mang tính chất tham khảo, không hardcode thành runtime constants):
  - Input: ~$0.10 / 1M tokens
  - Output: ~$0.50 / 1M tokens
  - Cache read: ~$0.01 / 1M tokens

### A3. TTS Strategy — Free-First, Vietnamese-Aware
- Candidate FREE chính: **Fish Audio S2.1 Pro Free** trên OpenRouter (`fish-audio/s2.1-pro-free:free`).
- Được thiết kế đa ngôn ngữ và hỗ trợ tiếng Việt mà không mất phí API.
- Dynamic Catalog Policy: Trạng thái miễn phí, tính sẵn sàng và identifier của free endpoint là động. Endpoint miễn phí này là một **development / testing / prototyping / low-volume candidate** và **KHÔNG PHẢI là dịch vụ production được đảm bảo (guaranteed production service)**.
- Trước khi đưa vào commercial production, LearnFlow bắt buộc phải kiểm tra và xác thực các điều kiện hiện hành:
  1. **Availability** (tính sẵn sàng của endpoint)
  2. **Pricing** (biểu phí phát sinh nếu chuyển tier)
  3. **Rate limits** (hạn mức gọi API)
  4. **License / commercial-use terms** (điều khoản bản quyền và sử dụng thương mại)
  5. **SLA** (cam kết chất lượng dịch vụ)
- Runtime tương lai PHẢI xác nhận model qua OpenRouter Models API / speech capability discovery thay vì giả định endpoint miễn phí tồn tại vĩnh viễn.

### A4. English Free TTS Fallback: `deepgram/flux-tts:free`
- Đối với bài học tiếng Anh, hỗ trợ thêm zero-cost candidate: Deepgram Flux TTS Free (`deepgram/flux-tts:free`).
- Không giả định Flux hỗ trợ tốt tiếng Việt. Không tự động route bài giảng tiếng Việt sang Flux trừ khi có cơ chế bilingual fallback được cho phép rõ ràng.

### A5. Edge TTS — Non-OpenRouter Emergency Fallback
- Edge TTS (từ V1) không bị loại bỏ hoàn toàn, mà trở thành **emergency fallback ngoài OpenRouter**, không cần paid API key.
- Vì chất lượng tiếng Việt của Edge TTS có thể chưa đạt tiêu chuẩn cao của V2, Edge TTS không được tự động vượt mặt một model OpenRouter hỗ trợ tiếng Việt đã vượt qua quality checks.
- Chuỗi fallback ưu tiên:
  - **Tiếng Việt**: `Fish S2.1 Pro Free` → *(nếu unavailable / quality reject)* → `Optional Paid OpenRouter TTS` *(nếu budget cho phép)* → *(nếu unavailable / paid disabled)* → `Edge TTS`.
  - **Tiếng Anh**: `Fish S2.1 Pro Free` → `Deepgram Flux TTS Free` → `Edge TTS`.
  - Thứ tự ưu tiên chính thức giữa các candidate sẽ được xác định bằng empirical benchmark.

### A6. Paid TTS Quality Escalation: `google/gemini-3.1-flash-tts-preview`
- Tùy chọn leo thang chất lượng âm thanh trả phí qua OpenRouter: `google/gemini-3.1-flash-tts-preview` (giá tham khảo: ~$1 / 1M text input tokens, ~$20 / 1M audio output tokens).
- Không phải default. Điều khiển bởi cờ chính sách: `allow_paid_tts` (mặc định development: `false`).
- Không bao giờ âm thầm tiêu tiền khi free provider gặp sự cố. Mọi chi phí phải được ghi nhận minh bạch vào `BudgetLedger`. (Không implement cờ này trong V2-02, chỉ tài liệu hóa).

### A7. Bilingual Fallback Policy
- Nếu ngôn ngữ yêu cầu (ví dụ: tiếng Việt) không thể synthesize đạt chuẩn bởi các free TTS hiện có: KHÔNG được âm thầm đổi ngôn ngữ narration sang tiếng Anh mà không thông báo.
- Runtime tương lai hỗ trợ flag cấu hình tường minh: `allow_bilingual_fallback = true`.
- Khi kích hoạt:
  - Narration audio: tiếng Anh (đọc bởi model chất lượng cao).
  - Subtitle: tiếng Việt (phụ đề chính xác theo nội dung bài giảng).
- Provenance và artifact metadata phải ghi nhận đầy đủ: `requested_language`, `spoken_language`, `subtitle_language`, `fallback_reason`.

### A8. Subtitles Derived from Structured Script (No Second GPT Call)
- `Script Agent` là đơn vị sở hữu toàn bộ ngữ nghĩa nội dung narration.
- Do đó, subtitle phải được sinh trực tiếp từ structured script artifact, bao gồm:
  - `spoken_text`
  - `subtitle_text`
  - `spoken_language`
  - `subtitle_language`
- Với bài giảng cùng ngôn ngữ: `spoken_text ≈ subtitle_text`.
- Với bilingual fallback: `spoken_text = English`, `subtitle_text = Vietnamese`.
- Script Agent tạo ra cả hai trường trong cùng một lượt structured generation duy nhất. Không gọi thêm một LLM call thứ hai chỉ để copy hoặc dịch narration sang subtitle.

### A9. Audio Alignment Strategy
- Khi nhận audio từ TTS provider:
  - Nếu provider trả về word-level timing metadata: sử dụng trực tiếp timing metadata từ provider.
  - Nếu provider không trả về timing metadata:
    - **Budget-first mode**: nội suy timing theo sentence/segment dựa trên structured script đã biết kết hợp thời lượng audio đo thực tế.
    - **Precision mode**: sử dụng mô hình phiên âm đa ngôn ngữ siêu tiết kiệm `openai/whisper-large-v3-turbo` qua OpenRouter để alignment chính xác từng từ. (Không implement STT trong checkpoint này).

### A10. Image Model Strategy
- Phân tầng generation ảnh qua OpenRouter khi visuals mang tính trực quan cao:
  - Deterministic SVG/Canvas visual → *(nếu không đủ diễn đạt)* → `google/gemini-3.1-flash-lite-image` → *(nếu critic reject)* → `google/gemini-3.1-flash-image`.
  - Sinh ảnh là tùy chọn theo nhu cầu từng scene, không bắt buộc sinh ảnh cho mọi scene.

### A11. Future Capabilities: Embedding & Reranking (V2D Only)
- Embedding và Reranking được quy hoạch cho phân hệ retrieval nâng cao ở V2D. Tuyệt đối không đưa vào V2A layout / measurement.
- Chiến lược OpenRouter: multilingual embedding model kết hợp reranking khi và chỉ khi benchmark chứng minh hiệu quả vượt trội.

### A12. Model Discovery Rule
- Nguyên tắc bất biến: Không bao giờ giả định một model ID sẽ tồn tại vĩnh viễn, luôn miễn phí, giữ nguyên giá hay giữ nguyên modalities.
- Trước khi tích hợp model capability, runtime phải verify metadata hiện thời qua OpenRouter Models API.
- Hợp đồng bền vững của hệ thống là **Capability Interface** (`ReasoningProvider`, `SpeechProvider`, v.v.), không phải một chuỗi model ID cứng.

### A13. Boundary Confirmation
- Toàn bộ tài liệu trên là đặc tả kiến trúc. Checkpoint V2-02 tuyệt đối không thêm runtime client, không thêm API keys, không thêm implementation cho TTS/STT/Image/Whisper/Hermes.

---

# 51. Skills của Hermes

Tạo:

```text
learnflow-research
learnflow-pedagogy
learnflow-script
learnflow-visual-direction
learnflow-scene-critique
learnflow-repair-policy
```

Hermes Skills là procedural memory, chỉ load khi cần thay vì nhét hết vào system prompt. Agent cũng có thể tự tạo/cập nhật skills. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md?utm_source=chatgpt.com))

Nhưng production nên để:

```text
skill update
→ review
→ approve
```

không cho agent silently thay đổi behavior.

---

# 52. Hermes Memory

Chỉ lưu preference bền:

```text
preferred video style
preferred language
learner level
preferred lesson length
```

Không lưu:

```text
scene status
render paths
temporary research
current retries
```

Những thứ đó phải nằm trong LearnFlow DB.

---

# 53. Hermes sessions không phải source of truth

Hermes có SQLite session persistence và compression/session lineage. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/agent-loop.md?utm_source=chatgpt.com))

Nhưng:

```text
HermesSession
!=
LearnFlowRun
```

Source of truth vẫn là:

```text
LearnFlow database
```

Hermes là reasoning runtime, không phải job database.

---

# 54. Kanban chỉ thêm sau

Hermes docs phân biệt rất rõ:

```text
delegate_task
→ parent cần kết quả ngay

Kanban
→ durable task, restart, handoff, human intervention
```

([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban.md?utm_source=chatgpt.com))

V2 đầu:

```text
delegate_task
```

V2 mature:

```text
Kanban
```

cho:

```text
research lane
visual lane
review lane
human approval lane
```

Worker lanes của Hermes hỗ trợ model/profile khác nhau và durable lifecycle. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/kanban-worker-lanes.md?utm_source=chatgpt.com))

---

# 55. Trajectory collection

Mình sẽ bật Hermes trajectory từ đầu.

Hermes có ShareGPT-compatible JSONL trajectory dùng cho debugging/training/evaluation. ([github.com](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/developer-guide/trajectory-format.md?utm_source=chatgpt.com))

Mỗi lesson nên giữ:

```text
trajectory.jsonl
research_pack.json
evidence_graph.json
lesson_plan.json
script.json
scene_graphs/
layout_reports/
motion_plans/
qa_reports/
repair_history.json
budget.json
final.mp4
```

Sau vài trăm run, chính đống dữ liệu này sẽ rất hữu ích để hiểu chỗ nào trong pipeline thực sự gây lỗi.

---

# 56. Project structure đề xuất — V1/V2 isolation trước migration

Không migrate V1 đang chạy ổn sang tree mới ngay khi bắt đầu V2.

V1 phải được freeze làm baseline và tiếp tục sống trong cấu trúc hiện tại:

```text
learnflow/
├── app/                 # V1 frozen production path
├── tests/               # V1 regression
├── scripts/
│
├── learnflow_v2/        # V2 side-by-side
│   ├── core/
│   │   ├── contracts/
│   │   ├── errors/
│   │   └── state/
│   │
│   ├── concepts/
│   │   └── registry.py
│   │
│   ├── scenegraph/
│   │   ├── schema.py
│   │   ├── normalize.py
│   │   ├── topology.py
│   │   └── compiler.py
│   │
│   ├── layout/
│   │   ├── router.py
│   │   ├── measurement.py
│   │   ├── constraints.py
│   │   ├── collision.py
│   │   ├── continuity.py
│   │   ├── score.py
│   │   ├── backends/
│   │   │   ├── kiwi.py
│   │   │   ├── elk.py
│   │   │   ├── graphviz.py
│   │   │   ├── timeline.py
│   │   │   ├── equation.py
│   │   │   └── grid.py
│   │   └── preflight.py
│   │
│   ├── motion/
│   │   ├── schema.py
│   │   ├── beats.py
│   │   ├── scheduler.py
│   │   ├── compiler.py
│   │   ├── transitions.py
│   │   ├── continuity.py
│   │   └── easing.py
│   │
│   ├── artifacts/
│   │   ├── manifest.py
│   │   ├── hashing.py
│   │   └── invalidation.py
│   │
│   ├── render/
│   │   ├── protocol.py
│   │   ├── pillow_ffmpeg.py
│   │   └── manim.py
│   │
│   ├── verification/
│   │   ├── deterministic.py
│   │   ├── frame_sampler.py
│   │   ├── anchor_overlay.py
│   │   ├── critic.py
│   │   ├── patch_schema.py
│   │   ├── repair.py
│   │   └── video_critic.py
│   │
│   ├── adapters/
│   │   └── v1_visual_intent.py
│   │
│   └── benchmarks/
│       ├── scenes/
│       ├── lessons/
│       └── regressions/
│
├── agents/              # only added after CORE GATE
│   ├── contracts/
│   ├── research/
│   ├── pedagogy/
│   ├── script/
│   └── visual/
│
└── .hermes/             # only after CORE GATE
    └── plugins/
        └── learnflow/
```

Migration rule:

```text
V1 remains default production path
while V2 is under Core Gate.
```

V2 receives input through adapters first:

```text
V1 LessonPlan / VisualIntent
→ V2 adapter
→ SceneGraph / ConceptRegistry
→ V2 engine
```

Only after benchmark proves V2 wins and Core Gate passes may routing change to:

```text
default_engine=v2
```

Rollback remains:

```text
default_engine=v1
```

for at least one stable release window.

---

# 57. Implementation roadmap

Roadmap vẫn giữ checkpoint nhỏ, nhưng execution được chia thành bốn milestone có thể benchmark và ship độc lập.

## Milestone V2A — Smart Static Engine

```text
V1 freeze
ConceptRegistry
SceneGraph
Intrinsic Measurement
Constraint Layout
Graph Layout
Collision / optimization
Adaptive typography
Deterministic LayoutPreflight / QA
```

Output:

```text
given a good storyboard
→ V2 tạo static educational scenes tốt hơn V1
```

Không cần Motion, VLM hay Hermes để V2A chứng minh giá trị.

## Milestone V2B — Motion Engine

```text
Motion Tier 1
Narration beats
Scheduler
MOVE continuity
InterSceneTransitionPlan
```

Output:

```text
video bớt slideshow
motion phục vụ narration
continuity measurable
```

## Milestone V2C — Self-Repair Engine

```text
Deterministic QA
QualityMode
VLM Critic
Patch DSL
Artifact invalidation
Selective repair
Video Critic
```

Output:

```text
local visual problem
→ local repair
→ only affected artifacts rebuild
```

## Milestone V2D — Hermes Agentic Layer

Chỉ bắt đầu sau CORE GATE:

```text
Research
Evidence
Pedagogy
Script
Visual Director
Budget / hooks
Skills
Kanban later
```

Output:

```text
autonomous evidenced lesson generation
```

---

## V2-00 — Freeze V1

Acceptance:

```text
all current CPs pass
end-to-end deterministic demo
golden output fixtures
V1 behavior frozen
```

Không bắt đầu V2 trước khi V1 có baseline ổn định.

---

## V2-01 — ConceptRegistry + SceneGraph schema

Implement:

```text
ConceptRegistry
canonical concept IDs
alias normalization
nodes
relations
groups
semantic keys
concept_ref
layout hints
style refs
versioning
```

Acceptance:

```text
Pydantic validation
stable serialization
100 fixture graphs
invalid graph rejected
unknown concept_ref rejected
registry key collisions rejected
cross-scene same concept resolves to same canonical identity
V1 VisualIntent adapter works
```

---

## V2-02 — Intrinsic measurement

Implement:

```text
text measurement
math measurement
asset size
wrap candidates
minimum readable bounds
```

Acceptance:

```text
measurement deterministic
font fixtures stable
no render required
```

---

## V2-03 — Layout zones + simple constraints

Implement:

```text
safe areas
grid
title/content/caption zones
Kiwi backend
```

Support first:

```text
concept card
comparison
image + text
quote
```

Acceptance:

```text
zero clipping on fixtures
symmetry tests
9:16 + 16:9
```

---

## V2-04 — Graph Layout

Implement:

```text
ELK adapter
Graphviz adapter
ports
orthogonal routing
```

Support:

```text
process
causal graph
hierarchy
flow
```

Acceptance:

```text
zero node-edge collisions
crossing score baseline
stable deterministic result
```

---

## V2-05 — Collision + optimization pass

Implement:

```text
collision detection
iterative constraint addition
layout score
candidate comparison
fallback strategies
```

Acceptance:

```text
dense fixture suite
no fatal overlap
no clipping candidate can outrank a feasible candidate
hard feasibility gate tested separately from soft ranking
bounded solver iteration
```

---

## V2-06 — Continuity Layout

Implement:

```text
semantic_key persistence
previous-layout soft constraints
stable graph order
```

Acceptance:

```text
same concepts move minimally
new concepts inserted without full reshuffle
```

---

## V2-07 — Motion Grammar Tier 1 schema

Implement trước tập tối thiểu:

```text
ENTER: FADE / SLIDE / REVEAL
EMPHASIZE: HIGHLIGHT / PULSE / FOCUS
RELATION: DRAW_EDGE / PROPAGATE
TRANSFORM: MOVE
EXIT: FADE
```

Tier-2/Tier-3 verbs remain schema-reserved hoặc deferred, không trở thành dependency của V2B.

Acceptance:

```text
invalid combinations rejected
no arbitrary animation command
versioned serialization
Tier-1 replay deterministic
no unsupported camera/morph requirement in basic scenes
```

---

## V2-08 — Narration Beat Alignment

Implement:

```text
word timestamps
phrase grouping
semantic beats
MotionPlan triggers
```

Acceptance:

```text
event timing follows narration
fallback works without word timestamps
```

---

## V2-09 — Motion Scheduler + Compiler

Implement:

```text
dependency DAG
conflict checks
motion budget
property tracks
```

Acceptance:

```text
no event after node removal
no conflicting camera animations
deterministic timeline
```

---

## V2-10 — Persistent transforms + InterSceneTransitionPlan

Implement:

```text
cross-scene semantic matching through ConceptRegistry
InterSceneTransitionPlan schema
MOVE as required baseline
renderer transition capability negotiation
FADE fallback for unsupported transitions
MORPH / RESIZE optional after MOVE baseline
```

Acceptance:

```text
persistent nodes do not unnecessarily fade when MOVE is supported
transition artifact is versioned/serializable
unsupported advanced transition falls back deterministically
transition renderer does not corrupt scene-local MotionPlan
```

---

## V2-11 — Deterministic QA

Implement:

```text
bbox checks
clipping
edge collision
safe zone
font size
duration
audio
blank-frame detection
```

Acceptance:

```text
known broken fixtures all detected
false positive rate measured
```

---

## V2-12 — Optional VLM Critic

Implement:

```text
quality_mode=deterministic|critic
event-aware frame sampling
ID overlay
anchor overlay
structured critic schema
critic provider failure policy
```

Acceptance:

```text
no prose response allowed
all outputs schema-valid
critic cannot assign pixels
deterministic mode makes zero VLM calls
critic outage does not break deterministic-approved output unless strict policy explicitly enabled
all VLM repairs pass deterministic re-check
```

---

## V2-13 — Repair Engine + dependency invalidation

Implement escalation:

```text
auto-fix
node patch
group patch
layout change
SceneGraph regeneration request
fallback
artifact content hashes
input dependency hashes
invalidation rules
cache reuse when hashes match
```

Acceptance:

```text
selective scene repair
max retries enforced
unchanged scenes not rerendered
geometry-only repair does not resynthesize audio
changed SceneGraph invalidates only required downstream artifacts
affected inter-scene transitions invalidated correctly
replay with identical inputs reuses deterministic artifacts
```

---

## V2-14 — Video Critic

Implement:

```text
cross-scene visual variety
continuity
style
pacing
pedagogical alignment
```

Acceptance:

```text
video-level issue points to specific scenes
```

---

# CORE GATE

Hermes chỉ bắt đầu khi:

```text
Render success            >= 98%
Fatal clipping            = 0
Fatal overlap             ~= 0
Invalid MotionPlan        = 0
Selective repair success  >= 90%
Reproducibility           = 100% for deterministic scenes
V1→V2 regression          = 0 critical product regressions
V2 static quality         > V1 baseline on agreed benchmark
VLM unavailable           does not break deterministic mode
Local repair              does not rebuild unaffected scenes
```

Và điều quan trọng nhất là:

```text
given a good storyboard
→ Core V2 consistently produces a good video
```

Nếu điều này chưa đúng thì thêm Hermes cũng chưa giải quyết được vấn đề gốc.

---

# 58. Hermes checkpoints

## H-01 — Hermes bootstrap

Pin Hermes version/commit.

Configure:

```text
OpenRouter
openai/gpt-6-luna
project AGENTS.md
trajectory logging
```

Smoke test:

```text
agent
→ tool
→ structured result
```

---

## H-02 — LearnFlow plugin

Expose capability tools.

Acceptance:

```text
Hermes can create/run/render
but cannot touch renderer internals
```

---

## H-03 — Agent contracts

Implement:

```text
LearningBrief
ResearchPack
EvidenceGraph
PedagogyPlan
LessonScript
Storyboard
AgentRun
BudgetLedger
```

---

## H-04 — Research orchestration

Implement:

```text
Director
   ↓
Research Orchestrator
   ↓
3 specialized researchers max
```

Acceptance:

```text
source provenance preserved
isolated contexts
bounded delegation depth
```

---

## H-05 — Fact verification

Every factual narration maps to:

```text
claim_id
```

Acceptance:

```text
unsupported claim blocked
contradictions flagged
```

---

## H-06 — Pedagogy Agent

Acceptance:

```text
objectives
prerequisites
concept progression
examples
misconceptions
```

required before script.

---

## H-07 — Script Agent

Acceptance:

```text
claim IDs preserved
teaching function per segment
no visual coordinates/code
```

---

## H-08 — Visual Director

Output:

```text
SceneGraph[]
```

Acceptance:

```text
100% schema-valid
layout hints semantic only
no pixel coordinates
```

---

## H-09 — End-to-end orchestration

```text
query
→ research
→ pedagogy
→ script
→ SceneGraph
→ Core V2
→ video
```

Chưa cần repair agents riêng ở checkpoint này.

---

## H-10 — Agent-aware QA

Hermes nhận:

```text
VLM repair report
```

Nếu semantic problem:

```text
Visual Director fixes graph
```

Nếu factual:

```text
Script / Research fixes claim
```

Nếu geometric:

```text
Core layout fixes it
```

Routing này rất quan trọng để lỗi được sửa ở đúng layer.

---

## H-11 — Hooks + Budget

Implement:

```text
pre_tool_call policy
post_tool_call metrics
agent lifecycle tracing
cost ledger
```

Acceptance:

```text
budget cannot be exceeded
illegal publication blocked
```

---

## H-12 — Skills

Tạo stable procedures.

Skills được review thủ công trước khi production dùng.

---

## H-13 — Kanban durability

Chỉ làm sau khi synchronous orchestration chạy ổn.

Use:

```text
research profile
production profile
review profile
```

cho long-running production.

---

# 59. Benchmark

Mình sẽ không gọi LearnFlow là “SOTA” nếu chưa có benchmark.

Benchmark bắt buộc có V1 frozen baseline để mọi improvement của V2 đo được A/B trên cùng storyboard/input.

```text
V1 deterministic renderer
vs
V2A static engine
vs
V2B motion engine
vs
V2C critic/repair
vs
V2D Hermes full system
```

Không đổi benchmark fixture giữa hai candidate trong cùng một comparison.

Tạo:

```text
LearnFlowBench
```

ban đầu khoảng 100 topics:

```text
CS
math
physics
biology
chemistry
history/general
```

chia:

```text
easy
medium
hard
```

Ngoài benchmark riêng, có thể chạy một subset của MMMC/Code2Video; Code2Video có 117 learning topics và đánh giá Knowledge Transfer bằng TeachQuiz, aesthetic/structural quality và efficiency. ([github.com](https://github.com/showlab/Code2Video?utm_source=chatgpt.com))

VisualEDU cho thêm các metric về temporal consistency, logical correctness và visual clarity. ([aclanthology.org](https://aclanthology.org/2025.findings-emnlp.889/?utm_source=chatgpt.com))

---

# 60. Metrics

## Structural

```text
render success
clipping
overlap
edge collision
scene failure
repair count
```

## Visual

```text
hierarchy
balance
readability
visual variety
layout quality
```

## Temporal

```text
audio-motion alignment
transition continuity
motion conflicts
```

## Semantic

```text
visual ↔ narration match
relation correctness
formula correctness
```

## Pedagogy

```text
objective coverage
example quality
concept progression
cognitive load
misconception handling
```

## Learning outcome

```text
TeachQuiz-style knowledge transfer
```

---

# 61. Ablation experiments

Ta nên chạy:

```text
V1 renderer

+ SceneGraph

+ Layout Solver

+ Motion Grammar

+ deterministic QA

+ VLM Critic

+ Repair

+ Hermes research

+ Hermes pedagogy
```

Như vậy sẽ biết chính xác component nào thực sự tạo ra improvement.

Không chỉ nhìn cảm giác “V2 đẹp hơn”.

---

# 62. Cost evaluation

Record:

```text
LLM tokens
VLM tokens
image generations
TTS
render time
repair time
```

Metric:

```text
cost / finished minute

cost / successful lesson

VLM calls / scene

repair cost / repaired scene
```

Target quan trọng:

> Không gọi VLM nếu deterministic checker đã đủ.

---

# 63. Regression strategy

Mỗi bug layout nên biến thành fixture.

Ví dụ:

```text
bug:
long equation clipped

→ fixture:
layout_long_equation_001
```

Sau nhiều vòng, LearnFlow sẽ tích lũy một bộ pathological cases rất mạnh.

Mỗi regression fixture nên lưu cả expected dependency behavior:

```text
input artifact hashes
expected invalidation set
expected reused artifacts
expected repaired artifacts
```

Như vậy regression suite không chỉ bắt visual output sai mà còn bắt việc engine rerender/resynthesize quá nhiều.

Đây là phần có thể tạo moat thực tế hơn nhiều so với chỉ đổi model.

---

# 64. Demo cuối cùng của V2

Input:

```text
Teach me backpropagation.

I understand basic algebra
but not calculus.

5-minute lesson.
```

Hệ thống phải tự:

```text
understand learner
       ↓
research
       ↓
evidence graph
       ↓
pedagogical plan
       ↓
script
       ↓
storyboard
       ↓
SceneGraph
       ↓
constraint layout
       ↓
motion planning
       ↓
render
       ↓
deterministic QA
       ↓
VLM QA
       ↓
scene repair
       ↓
video QA
       ↓
publish
```

Ví dụ Scene 7 quá đông:

```text
VLM:
COGNITIVE_OVERLOAD

         ↓

Patch:
split group

         ↓

Layout Engine
recomputes positions

         ↓

render Scene 7 only

         ↓

PASS
```

Không sửa Python.

Không render lại 12 scene khác.

---

# 65. Artifact cuối run

```text
run/
├── learning_brief.json
├── research_pack.json
├── evidence_graph.json
├── pedagogy_plan.json
├── script.json
├── storyboard.json
├── concept_registry.json
│
├── scenegraphs/
│   ├── 001.json
│   └── ...
│
├── layouts/
├── motion/
├── transitions/
├── artifact_manifests/
├── frames/
├── scenes/
│
├── verification/
│   ├── deterministic.json
│   ├── vlm.json
│   └── video.json
│
├── repair_history.json
├── invalidation_history.json
├── provenance.json
├── budget.json
├── trajectory.jsonl
│
└── final.mp4
```

Một run phải replayable và explainable từ đầu đến cuối.

---

# 66. Những thứ tuyệt đối không agentize

Giữ deterministic:

```text
geometry
layout constraints
timeline arithmetic
artifact paths
state transitions
codec validation
schema validation
cost accounting
retry accounting
atomic publication
renderer implementation
security policy
```

Agentize:

```text
research strategy
evidence judgment
pedagogy
narrative
visual metaphor
semantic visual selection
semantic QA
repair intent
```

Mình xem đây là boundary quan trọng nhất của toàn bộ V2.

---

# 67. Kiến trúc cuối

```text
┌─────────────────────────────────────┐
│          HERMES CONTROL PLANE       │
│                                     │
│ Director                            │
│ Research delegation                 │
│ Evidence                            │
│ Pedagogy                            │
│ Script                              │
│ Visual direction                    │
│ Semantic QA                         │
│ Skills / Memory / Kanban            │
└─────────────────┬───────────────────┘
                  │
                  │ typed artifacts
                  ▼
┌─────────────────────────────────────┐
│        LEARNFLOW CORE V2            │
│                                     │
│ SceneGraph                          │
│ Layout Engine                       │
│ Motion Grammar                      │
│ Renderer                            │
│ Deterministic QA                    │
│ VLM Critic                          │
│ Scene Repair                        │
│ QualityGate                         │
└─────────────────┬───────────────────┘
                  │
                  ▼
              final.mp4
```

Hermes = **brain + director**.

ConceptRegistry = **semantic identity across the lesson**.

SceneGraph = **visual language**.

Layout Engine = **geometry intelligence**.

Motion Grammar = **animation language**.

InterSceneTransitionPlan = **cross-scene continuity contract**.

Artifact dependency graph = **selective rebuild contract**.

VLM Critic = **optional eyes**.

Repair Engine = **feedback loop**.

Renderer = **hands**.

---

# 68. Thứ tự thực hiện bắt buộc

Mình sẽ không triển khai tất cả cùng lúc.

```text
V1 freeze + golden baseline
   ↓

V2A — Smart Static Engine
ConceptRegistry
SceneGraph
Measurement
Layout / typography / preflight
   ↓

V2A benchmark vs V1
   ↓

V2B — Motion Engine
Motion Tier 1
Semantic beats
InterSceneTransitionPlan
   ↓

V2B benchmark vs V2A
   ↓

V2C — Self-Repair
Deterministic QA
Optional VLM Critic
Dependency invalidation
Selective repair
Video Critic
   ↓

CORE GATE / CORE FREEZE
   ↓

V2D — Hermes
plugin
research
evidence
pedagogy
script
Visual Director
agent QA routing
budget / skills
Kanban later
   ↓

Full benchmark
```

Nếu làm Hermes trước:

```text
smart agent
+
weak renderer
=
smart system producing mediocre videos
```

Còn hướng mình muốn là:

```text
strong production engine
+
smart agent
=
LearnFlow V2
```

# Definition of Done

Mình chỉ xem LearnFlow V2 là hoàn thành khi một user query có thể đi xuyên suốt:

```text
query
→ autonomous research
→ evidenced lesson
→ pedagogy
→ script
→ semantic storyboard
→ SceneGraph
→ constraint layout
→ narration-aware motion
→ rendering
→ deterministic verification
→ multimodal critique
→ selective repair
→ final video
```

với các invariant:

```text
no arbitrary generated rendering code

no manually generated pixel coordinates

canonical semantic identity through ConceptRegistry

no whole-video regeneration
for local visual problems

explicit dependency/invalidation manifests

cross-scene continuity represented by typed transition artifacts

VLM optional for deterministic-approved output

full provenance

bounded cost

reproducible deterministic scenes

repairable semantic artifacts

V1 rollback path preserved until V2 core is proven
```

Đó là kiến trúc mình sẽ chọn nếu mục tiêu của bạn là đưa LearnFlow từ coding-challenge MVP thành một hệ thống educational video generation có chiều sâu kỹ thuật thực sự, đủ để benchmark nghiêm túc với hướng Code2Video/TheoremExplainAgent, thay vì chỉ gắn thêm “multi-agent” lên trên một renderer còn yếu.

---

# V2.1 Revision Summary

Bản V2.1 này tích hợp trực tiếp các hardening sau vào plan gốc:

```text
ConceptRegistry
InterSceneTransitionPlan
feasibility-first layout scoring
adaptive typography order correction
Motion Grammar capability tiers
optional VLM QualityMode
artifact dependency hashes + invalidation
V1/V2 side-by-side isolation
V2A/V2B/V2C/V2D milestone gates
V1-vs-V2 benchmark discipline
```

Các nguyên tắc không thay đổi:

```text
semantics by LLM/agents
geometry deterministic
motion constrained by grammar
pixels by renderer
critic cannot write executable rendering code
local failures repaired locally
final publication only after verification
```
