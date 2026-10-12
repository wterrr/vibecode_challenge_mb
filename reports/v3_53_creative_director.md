# V3-53 — Evidence-Grounded Creative Director & Composable Semantic Motion

**State:** Code submitted; exact-head native CI and MP4 independent inspection PENDING. Parent Draft PR #86 exact commit `2be42bdfe4d0c242b67e8bfed3bae4f4e19ec9ff`; first child commit `959577a` preregistered tests/cases before implementation.

## Gap, hypothesis, protocol

V3-52 provided physically causal weight-to-context motion but compiled a fixed four-beat attention choreography. V3-51 accepted flexible SceneGraphs but mainly authored visual reveals and links. V3-53 adds a separate **prospective model-facing** typed director IR with 4 required semantic stages plus independently selectable optional intro and inspect beats, authored visual focus and trace/compare/spotlight per beat, and authored style. The host enforces the actual causal partial order (compare → normalize → transport → compose) and validates every claim ID and fact SHA against computed QKV arithmetic. Context inspection is only allowed once context exists. No arbitrary Python, numerical claims or provider code can enter Manim.

Source topic is limited to one two-token Attention basis: Q=[1,0] or [0,1], K and V basis, d_k=2. Original V3-52 exact math, V2 SceneGraph validation and native renderer/audio Docker helpers are reused. The resulting semantic event compiler is keyed by **operator**, not by a fixture ID. It generates value-to-contribution and normalized-weight-to-context transforms in the same scene and uses host-fact-derived geometry. This is **bounded composability**, not generic visual generation across all subjects.

## Preregistered frozen cases and acceptance

1. `network_causality` host-authored stages intro → compare → normalize → transport → compose, style network, Q=[1,0].
2. `bar_first` stages compare → normalize → inspect → transport → compose, style weighted_bars, Q=[1,0].
3. `counterfactual_b` stages intro → compare → normalize → transport → compose → inspect, style value_mixture, Q=[0,1].

The model-facing IR must change real objects/ops and results, not only names. Test adversarial forbidden stage orders, missing stages, evidence-digest spoof, forged model origin, wrong focus, injected code, unsupported QKV, and copy bypass. All frozen V3-50/51/52 and V2/Bench safety gates must pass. Render **three native actual H264/AAC files**, prove the context ROI empty before value transport and two correctly proportioned colored segments present after, verify the physical Q counterfactual and audio-exact frame budget, and audit actual frames independently.

## Scientific honesty

All three storyboard plans are **HOST_SYNTHETIC_NOT_MODEL**; no additional model API call after consumed V3-50 authorization. Genuine provider-produced SceneGraph compatibility and arbitrary creative AI storytelling are not tested. Human educational effect, full semantic truth of arbitrary narration, animation quality at 3Blue1Brown level, and multi-domain generality are not certified. Production BLOCKED, main unchanged, PR Draft. **No final PASS until exact HEAD CI and downloaded real MP4 evidence.**
