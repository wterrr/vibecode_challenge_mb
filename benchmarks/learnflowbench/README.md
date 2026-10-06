# LearnFlowBench

LearnFlowBench is the frozen evaluation harness for comparing LearnFlow architectural milestones without changing the input to favor a candidate.

Status: IMPLEMENTED_AWAITING_CI.

## Frozen corpus

`corpus_v1.json` contains exactly 100 topics across:

- computer science: 17
- mathematics: 17
- physics: 17
- biology: 17
- chemistry: 16
- history/general: 16

Difficulty is fixed at 34 easy, 33 medium, and 33 hard topics.

After acceptance, this file is immutable. Future changes require a new corpus version rather than editing V1 in place.

## Candidate milestones

The benchmark configuration defines:

```text
V1  = frozen legacy deterministic renderer
V2A = SceneGraph + Layout Solver (static)
V2B = V2A + Motion Grammar + transitions
V2C = V2B + deterministic QA + critic/repair capability
V2D = V2C + Hermes control plane
```

## Two evidence tracks

### Core ablation

V1/V2A/V2B/V2C consume the exact same three frozen V1 `LessonPlan` fixtures:

```text
photosynthesis
ram_vs_ssd
tcp_three_way_handshake
```

The runner renders real MP4s and measures structural metrics, a narrow deterministic static-composition proxy, temporal capability counts, repair success for V2C fault injection, and wall-clock rendering cost.

No candidate-specific storyboard edits are allowed.

### V2D full-system fixture replay

V2D runs the accepted typed Lesson Pipeline through Research → Fact Verification → Pedagogy → Script → Visual Director → Core → final video using the existing deterministic fixture runner.

This proves full-system integration and typed semantic/pedagogy integrity, but it is **not** presented as an apples-to-apples quality comparison with the three core fixtures and it is not a live-provider quality result.

## Measurement honesty

Every observation is one of:

```text
MEASURED
UNMEASURED
NOT_APPLICABLE
```

A MEASURED result must carry evidence. UNMEASURED and NOT_APPLICABLE results cannot carry numeric values.

LearnFlowBench V1 deliberately blocks a SOTA claim. In particular, CI does not fabricate:

- TeachQuiz-style learning outcome;
- live LLM/VLM token usage;
- live provider USD cost;
- human aesthetic score;
- 100-topic live V2D generation results.

Those require a later governed live evaluation protocol on the frozen corpus.

## Commands

```bash
python scripts/verify_learnflow_bench.py
pytest -q --confcutdir=tests/hermes tests/hermes/test_learnflow_bench.py
python scripts/run_learnflow_bench.py benchmark_output/learnflowbench
python scripts/verify_v2_core_freeze.py
```

The executable benchmark writes `benchmark_output/learnflowbench/report.json` and raw core-ablation evidence. Generated MP4/frame artifacts are CI artifacts and are not committed as golden media.
