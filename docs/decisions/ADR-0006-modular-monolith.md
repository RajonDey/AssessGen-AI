# ADR-0006 — Modular monolith, not microservices

**Status:** Accepted · **Date:** 2026-07-30

## Context

The system has several plausibly separable concerns: an API, generation workers, a quality engine, an
audio pipeline, a publishing service. The original vision diagram shows them as distinct boxes, which
invites a service-per-box reading.

Meanwhile the team is very small, and the development machine has 16 GB of memory.

## Decision

One deployable backend (a modular monolith) plus one frontend. Internal boundaries are enforced by an
**import-linter layer contract in CI** rather than by network calls.

Celery workers run the *same* codebase in a different process — a deployment topology, not a service
boundary.

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| Microservices per concern | Distributed transactions, network failure modes, N deploy pipelines, N× local memory. Buys independent scaling we do not need |
| Separate quality service | The rule engine is pure functions over content. A network hop to run `str.find()` is indefensible |
| Separate audio service | Tempting (different resource profile) — but a queue with its own concurrency achieves the same isolation without a service |
| Serverless functions | Cold starts against multi-minute model calls; local development becomes awkward |

## Consequences

**Positive**
- One codebase, one test suite, one deploy, one migration path.
- Transactional consistency across content, quality checks and provenance — no sagas.
- Local development actually fits in 16 GB.
- Refactoring across boundaries is a normal code change, which matters a great deal while the design
  is still settling.

**Negative**
- Cannot scale components independently. Mitigated substantially by separate Celery queues with
  independent concurrency, which is where the real resource asymmetry lives.
- Boundary discipline depends on CI enforcement rather than physics. Import-linter is therefore not
  optional tooling.
- A deploy ships everything.
- Long-term risk of coupling creep if the layer contract is ever weakened.

**Neutral**
- The layer contract keeps a future extraction cheap: a well-isolated layer with no upward
  dependencies is exactly what a service needs to become one.

## Reversal criteria

- The audio pipeline needs GPU hardware the API does not — extract it first, it is the most naturally
  separable component and already has its own queue.
- Team grows past ~8 engineers and merge contention becomes a real cost.
- A tenant requires a physically isolated deployment.
- One component's scaling profile genuinely diverges (e.g. the consumer API needs global edge
  distribution while generation stays central).

Extraction is intended to be incremental — strangle one bounded component at a time, starting with
whichever has the fewest upward dependencies. The layer contract exists partly to keep that option
open.
