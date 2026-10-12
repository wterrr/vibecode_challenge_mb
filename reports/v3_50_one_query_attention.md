# V3-50 — One genuine model query about Transformer Scaled Dot-Product Attention

**Current status:** staged for exact-head OFFLINE CI; not yet an executed live inference. This is a one-query model-authored lesson prototype, not domain generalization.

## User's request and authorized scope

"test thử 1 query hỏi về model transformer hay attention trên model thử" authorizes a bounded real model test (one query). This checkpoint uses the exact preregistered user query in `benchmarks/learnflowbench/v3/v3_50_attention_one_query_preregister.json`, model `openai/gpt-6-luna` via existing OpenRouter secret **only after offline CI SUCCESS**. Max one HTTP POST, max_tokens 2800, no retries/provider fallback/temperature; no model request on PRs, ordinary pushes or reruns. Historical V3-42 single-shot budget remains consumed, never rerun.

## Research question

Can ONE fresh real model response create original, claim-anchored narration and stage-level visual emphasis for a concept beyond fractions (scaled dot-product attention), and pass the existing safe host-owned Manim → H264/AAC pipeline?

## Ground truth: verified QKV example

From Vaswani et al., 2017, equation Attention(Q,K,V)=softmax(QK^T/sqrt(d_k))V, source https://arxiv.org/abs/1706.03762 . Focus: one self-attention query, two keys and values, one head, no causal mask. Numeric fixture Q=(1,0), K_A=(1,0), K_B=(0,1), V_A=(1,0), V_B=(0,1), d_k=2. Host independently computes scores (1/sqrt(2),0), weights approximately (.670,.330) and context approximately (.670,.330). The example is manually chosen for teaching, not learned weights from an actual Transformer.

## Strict model-authoring contract

Four mandatory claim-anchored beats A1–A4: explain Q/K/V; dot-product plus scaling; softmax attention weights; weighted sum of V. The model supplies original spoken narration, title/objective, stage-specific focus, visual style and pace via a provider-portable strict JSON Schema. Stage values and vector arithmetic are HOST verified, never copied from model calculations. Host produces finite Manim code with geometric attention arrows, softmax probability bars and value-to-context transformation. No executable provider-authored Python.

Live POST records provider/model response SHA and validated JSON hash; model-origin is only claimed on a genuine provider reply and native decoded media. A local synthetic JSON fixture is always explicitly marked synthetic. The scene model can select emphasis; it does NOT choose arbitrary scene topology, which is an important research limitation.

## Gate sequence

1. Preregister FIRST at commit `f699a83` on Draft branch extending PR #83 HEAD `bdc4d6a`.
2. Implement protocol/provider/mock negative tests, native offline MP4 and old benchmark/safety regressions. All ordinary CI remains 0-POST.
3. Verify exact implementation HEAD CI SUCCESS and synthetic MP4 by physical SHA/codec/frames/decoded samples, never confuse with real output.
4. Only then make exactly ONE separately tagged activation commit `[v3-50-single-attention-model-post]`; the unique live job runs after its own same-commit offline gate. No second tagged commit / rerun / provider fallback.
5. Inspect model receipt + real MP4 with source/beat/QA; if provider/schema/semantic/render failure, one-shot consumed and mark NO-GO.
6. Even model-to-MP4 technical PASS cannot establish human comprehension, expert visual polish, cross-domain generalization or production readiness.

## Evidence status

Actual offline CI, one real HTTP call, model response SHA, native media SHA, human evaluation: **NOT YET REPORTED**.
