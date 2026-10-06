# Evidence Policy

## Grounding standard

A factual claim is eligible for narration only when deterministic verification can reach grounded source evidence through the EvidenceGraph and no contradiction or unresolved uncertainty blocks it.

## Semantic reviewer authority

Semantic review can make the system more conservative:

- `CONTRADICTED` blocks.
- `UNCERTAIN` blocks.
- `SUPPORTED` does not override missing deterministic evidence.

## Provenance preservation

Keep source locators and identifiers attached to the evidence they came from. Do not merge two sources into one invented source. Do not convert a claim-to-claim cycle into evidence unless a path from the cycle reaches a real source node.

## Repair discipline

For a routed factual repair, limit changes to the affected claim/evidence scope. The downstream Pedagogy/Script stages re-run their own gates after the repaired research artifact is accepted.
