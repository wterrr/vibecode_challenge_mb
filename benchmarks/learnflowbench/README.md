# LearnFlowBench

LearnFlowBench is the frozen evaluation harness for comparing LearnFlow architectural milestones without changing the input to favor a candidate.

Status: **DETERMINISTIC_ABLATION_PASS / LIVE_EVAL_PENDING**. CI run `37468207742` accepted the frozen 100-topic corpus and executable deterministic benchmark tracks. This does not mean the 100-topic live V2D study has been run.

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


## Accepted deterministic results

Accepted head: `2e341bb582b33bf3e1b8ccca8bf8efafc26d24eb`  
LearnFlowBench CI: `37468207742`  
Existing V2 Core Benchmark on the same head: `37468207743`  
Contract tests: **15 passed**  
Core Freeze: **PASS**

| Candidate | Real render | Static proxy | Structural / temporal evidence | Wall time |
| --- | ---: | ---: | --- | ---: |
| V1 | 3/3 | 66.15013163 | frozen legacy baseline | 5.79 s |
| V2A | 3/3 | 72.2185595 | clipping 0, overlap 0, motion 0, transitions 0 | 8.334997 s |
| V2B | 3/3 | 72.21820353 | clipping 0, overlap 0, motion events 9, transitions 6 | 9.193563 s |
| V2C | 3/3 | 72.21820353 | QA 9/9, selective repair 9/9 | 9.364739 s |

On this frozen deterministic proxy, V2A improves over V1 by **+6.06842787 points**. This is a narrow static-composition proxy and must not be presented as a human aesthetic score.

The V2D fixture replay also passed a real final-video path with 7 typed stages, objective coverage = 1.0, and selected-claim preservation = 1.0. Its provider token counts, provider USD cost, TeachQuiz learning outcome, and human visual quality remain explicitly **UNMEASURED** because the accepted CI run does not use a representative live-provider study.

The accepted CI artifact contains 141 files (artifact ID `11415308483`, archive SHA-256 `77aa9b0527673b1c87efafee3599707503dd9c39f3fabad403e2e0a20e9ef93f`).

## Remaining benchmark work

The next evaluation stage is **Governed Live V2D Evaluation** on the frozen 100-topic corpus. It must use a fixed provider/model policy and record real LLM/VLM tokens, USD cost, failures/retries, semantic/pedagogy metrics, and a fixed learning-outcome protocol. A SOTA claim remains blocked until those measurements exist and any external comparison protocol is actually executed.
