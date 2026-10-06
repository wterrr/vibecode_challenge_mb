# Publication Readiness Gates

A rendered lesson is not automatically publishable.

## Required before a READY verdict

- complete typed artifact chain;
- factual provenance intact;
- all stage readiness gates accepted;
- Core render artifacts present;
- authoritative scene/video QA non-blocking;
- routed repairs re-verified;
- replayable manifests present;
- budget/governance evidence present;
- no unresolved strict critic failure;
- no stale or unknown artifact references.

## Governance separation

The readiness verdict does not mutate `GovernanceState.publication_authorized`. Publication authorization is operator-owned. A model-facing tool argument cannot grant it.

If the publication tool is blocked by `pre_tool_call`, report the policy refusal and stop.
