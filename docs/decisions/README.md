# Architecture Decision Records

Each ADR records a decision that is **expensive to reverse**, the alternatives considered, and — most
importantly — **what evidence would justify reversing it**.

That last section is the point. A decision without reversal criteria becomes dogma: nobody remembers
why it was made, so nobody feels able to change it even when the situation clearly has.

## Index

| # | Decision | Status |
|---|----------|--------|
| [0001](ADR-0001-immutable-versioning.md) | Immutable content versioning | Accepted |
| [0002](ADR-0002-quality-gate-ordering.md) | Deterministic rules before LLM judgement | Accepted |
| [0003](ADR-0003-pgvector.md) | pgvector instead of a dedicated vector database | Accepted |
| [0004](ADR-0004-llm-gateway.md) | Custom LLM gateway instead of LiteLLM | Accepted |
| [0005](ADR-0005-tenancy-hedge.md) | `organization_id` from day one | Accepted |
| [0006](ADR-0006-modular-monolith.md) | Modular monolith, not microservices | Accepted |

## Writing a new one

Copy [ADR-0000-template.md](ADR-0000-template.md). Number sequentially. Never edit an accepted ADR to
change its decision — supersede it with a new one and mark the old `Superseded by ADR-XXXX`. The
history of what we believed and when is itself valuable.
