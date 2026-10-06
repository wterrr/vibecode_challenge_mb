# LearnFlow V2 Frozen Core Gate Baseline

Official engine commit:

```text
fdad3db1340d8b28175ab5382d800ff79df9a8a0
```

Benchmark: `v2-core-gate-v2`

Official GitHub Actions run: `37412433812`  
Official Actions artifact ID: `11389249199`  
Artifact digest: `sha256:5f5b167471779668f0c51b34090d2f54521f974019e294bef26c9a9d3e69e242`  
Raw `result.json` SHA-256: `16ee5c9f5684b53596f890e3978147e11c7df33f281bd48955a8bd01e2fe2609`  
Frozen spec SHA-256: `e20ab43e2a7622af8dc47c00c0c5692b42cceb05723ec93a70981effd62a9cfd`

The official run executed **959 V2 tests** before the benchmark and then produced the complete
3-lesson / 9-scene evidence corpus. Binary videos, frames and repair clips remain in the GitHub
Actions artifact; the repository stores the compact result plus exact Core Gate evidence/report.

Official decision: **CORE GATE PASS**.

The preceding `v2-core-gate-v1` result is invalidated and must not be used: its V1 static-quality
frames included burned subtitles while the V2 frames did not, and its text-fit measurement contract
was weaker. `v2-core-gate-v2` corrects both issues while preserving the same three frozen lessons.

`static_composition_proxy_v2` is a narrow deterministic composition proxy. It is **not** a human
aesthetic score and does not support a claim of 3Blue1Brown-level visual quality.

Coverage note: the three frozen lessons do not exercise a persistent-object MOVE transition; CP2.10
has dedicated contract/regression coverage for that behavior, but this benchmark should not be cited
as end-to-end persistent-MOVE evidence.
