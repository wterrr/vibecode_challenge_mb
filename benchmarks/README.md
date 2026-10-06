# LearnFlow Benchmarks

This directory contains benchmark fixtures and frozen baselines used to evaluate LearnFlow across architectural milestones.

## Structure

```text
benchmarks/
├── README.md
├── fixtures/
│   └── v1/
│       ├── tcp_three_way_handshake.json
│       ├── photosynthesis.json
│       └── ram_vs_ssd.json
└── baselines/
    └── v1/
        └── baseline.json
```

- `fixtures/v1/`: Reproducible structured V1 lesson inputs (canonical `LessonPlan` fixtures) that do not depend on external Gemini or LLM calls.
- `baselines/v1/`: Objective V1 baseline manifests and metrics captured from deterministic downstream pipeline runs (scene counts, intent sequences, codecs, dimensions, duration invariants, QualityGate pass).

## Guidelines

- Do **NOT** commit generated runtime MP4/WAV media files as golden fixtures.
- Do **NOT** use binary MP4 hashes as golden criteria; invariant ranges (codecs, dimensions, stream types, duration bounds) are used instead.
- The V1 baseline represents LearnFlow V1 CP10.


## V2 Core Freeze

After the corrected V2 Core Gate PASS, the accepted engine/evidence/rollback boundary is recorded in
`benchmarks/core_freeze/manifest.json`. Verify it with:

```bash
python scripts/verify_v2_core_freeze.py
```

The freeze is intentionally stricter than the benchmark baseline: it protects the accepted Core source
surface and rejects silent source/evidence drift before V2D/Hermes integration.
