# V3-51 — Creative Authoring Freedom & Evidence-Grounded Scene Compilation

**Status:** Implementation submitted, exact HEAD CI and MP4 inspection NOT YET CERTIFIED. No new model query, no live provenance claim, no main merge. Parent Draft PR #84 exact HEAD 1ef31e132659b2a7d07e351f0810824c91bc28ee.

## Why not widen V3-50 keyword validator

The actual V3-50 GPT-6 Luna single POST consumed its budget; V350_SCHEMA_OR_CLAIM_REJECTED was reported after receiving JSON, but the runner grouped structural and semantic errors and retained no sanitized stage/path diagnostics. Model correctness cannot be inferred from that failure.

V3-50 also provided only fixed A1..A4 scene choreography, fixed object locations, with model freedom limited to title, narration, focus enum, style and pace. That is a template, not creative scene authoring.

## Preregistered scientific gates

Before code, the first child commit 234c543 froze benchmarks/learnflowbench/v3/v3_51_creative_scene_preregister.json, including three distinct offline HOST storyboards:

- tokens_as_network: token match and value-flow network, 2 scenes
- scores_as_comparison: comparative weight bars and output derivation, 3 scenes
- heldout_symbolic_rewrite: freeform mathematical composition and weighted-value result, 3 scenes

These are variations within one frozen attention topic, not new domains or an unseen independent AI sample. Do not claim model creative generalization.

## Reuse-first implementation

- learnflow_v3/creative_scene_graph.py provides a versioned strict but expressive data contract: scene sequence, variable 3–7 narration beats, layout PROCESS/COMPARISON/GRID/FREEFORM, object kinds SHAPE/TEXT/MATH/EQUATION/CHART, flexible node IDs, safe nonnumeric labels, verified fact_ref, typed relations and six visual operations.
- A model-facing future contract can choose object identity/topology/composition/action timing instead of only choosing existing visual effects. Provider portability and inference acceptance are not tested.
- Every graph is mapped to and validated by the existing V2 SceneGraph for node, relation, layout identity. The shared V3-46 academic palette and CMU Serif font are reused. The existing V3-47 finite semantic grammar is retained for its prior families; V3-51 introduces a separate scene-level IR because fixed fraction/process claim IDs cannot truthfully describe arbitrary attention topology.
- Evidence labels, weights and numeric values come exclusively from a typed host ledger recomputed from the original V3-50 Q,K,V attention example. Relations are whitelisted host-evidence correspondences. A replacement requires stable identical underlying fact IDs, not an arbitrary misleading identity. Text-only labels cannot assert equations or unsupported digits. Free narration need not repeat exact English keywords.
- One generic compiler consumes all validated scene graphs and produces Manim source. No case ID dispatch and no model Python. Existing WAV-exact audio, network-isolated Manim Docker and native H264/AAC mux are reused.
- creative_validation_diagnostics.py separately classifies offline structural JSON Schema vs host semantic errors in V3-50; the new IR reports structure, evidence and graph/layout. Only sanitized paths, keywords and codes; never raw model text. Cannot retroactively explain the consumed V3-50 response.
- Negative mutants include SHA spoof, math hallucination in free labels, invalid edges/identities/target refs, cross-scene actions, duplicate IDs, wrong claim bindings, scene revisits, unproven object replacements, static scenes, and bad timing. Frozen V2/V3 tests and benchmark contracts remain.

## Minimum acceptance and limits

Only after exact HEAD CI succeeds, compare all three MP4 SHA hashes, 1280x720 H264/AAC timing, three normalized-time decoded frames from every output, pairwise visual differences and per-storyboard topology. Different pixels demonstrate different native compositions, NOT measurable creativity quality or comprehension benefit.

**Claim scope:** numeric/visual fact references are grounded; freeform narration truth remains NOT independently fact-checked and needs future verification. No live model output; no cross-domain generalization, human quality result or production readiness. Keep Draft PR stacked on #84. Production BLOCKED; no additional provider POST or retry.


### V3-51 — Exact-code offline evaluation closeout (2026-10-12)

**Code HEAD** b35f228f3502501d6363326180312e203d1b56d3 after collision/typography repair; [Push CI #38217494640](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38217494640) SUCCESS, **201 pytest PASS**, V3_BENCHMARK_PREREG/LEARNFLOW_BENCH_CONTRACT/CORE_FREEZE PASS. [Artifact #11733395546](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38217494640/artifacts/11733395546) independently downloaded and inspected after fixing silent artifact-upload path skip. Three **HOST SYNTHETIC** native H264/AAC 1280x720 15fps: tokens_as_network 632 frames/42.133 s SHA d40be20d38b2c3e6a70817bacc1fd61485048bb8cf6fb643cb403843ef24247b; scores_as_comparison 623 frames/41.533 s SHA 86a5f4ccb50cbc6e50c49fd365e09d063ebc1c6f14a5ae9f0c8a0b47e44d991a; heldout_symbolic_rewrite 788 frames/52.533 s SHA 2036476f17f7150eb1ae094714699bd068a27bc59afa752e01e9430c10ffd841. All native file SHA and H264/AAC tracks match physical receipts.

Decoded frame samples show each video nonstatic; normalized-time pairwise MAE sets [4.29,2.59,4.84], [4.94,3.01,5.57], [4.16,4.53,1.72]. This proves **render-distinct composition** only, not learner effectiveness. Initial visual audit found arrows crossing factual labels, tiny context, and sparse screen use. Generic compiler patch routes around obstructing nodes, increases comparison clearance, avoids enlarging short labels, wraps long verified formulas and adds scene headings. Final actual contact sheets show arrows clearer and context more legible but still mostly reveal/connect and sparse academic blackboard. Scientific verdict **BOUNDED CREATIVE SCENEGRAPH IR / NATIVE OFFLINE TECHNICAL PASS; ARTISTIC AND HUMAN PEDAGOGY NOT CERTIFIED**. NOT live model output, NOT 3Blue1Brown-level certification, NOT general subject transfer. Model-facing provider schema support and free narration truth checking NOT VERIFIED. Model requests 0; V3-50 spent live trial remains CLOSED; main unchanged, Draft PR #85, production BLOCKED. [PR CI #38217502498](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/38217502498) was queued at documentation time. This documentation-only closeout did not alter code; exact docs-HEAD CI requires separate confirmation.
