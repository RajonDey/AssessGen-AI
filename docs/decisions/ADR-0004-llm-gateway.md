# ADR-0004 — Custom LLM gateway instead of LiteLLM

**Status:** Accepted · **Date:** 2026-07-30

## Context

The production model choice is deliberately deferred until benchmark data exists. That deferral is
only real if no application code knows which model it is talking to — otherwise "swap the model"
becomes a refactor, and the deferral was an illusion all along.

Two further constraints shape the requirement:

1. **16 GB unified memory.** Only one large model may be resident. Ollama will happily load a second
   on request and then swap to disk or fail; both outcomes are worse than waiting.
2. **Provenance is a product feature.** Every generation must be reproducible, which requires
   capturing prompt hash, model digest, seed and sampling parameters into *our* schema.

LiteLLM (1.94.0) is the obvious off-the-shelf option.

## Decision

Write a thin internal gateway (~300 lines) in `infrastructure/llm/`, over `langchain-ollama` now and
official provider packages later. No other module may import a provider SDK — enforced by an
import-linter contract in CI.

Callers request a **role** (`generator`, `critic`, `metadata`, `embedding`), never a model name.

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| **LiteLLM** | Solves ~60 % of our need. No model-lease concept, model-name routing rather than role routing, own provenance format. We would write the other 40 % anyway and own an abstraction we did not design |
| **LangChain model abstractions directly** | Good abstraction, but no place for leasing, role routing or our accounting. Agents would call models directly, losing the choke point |
| **Direct provider SDKs in agents** | Fastest to write, destroys the deferral. Every model change becomes a cross-cutting refactor |
| **OpenRouter / proxy service** | External dependency and cost; conflicts with local-first development |

## Requirements the gateway satisfies

| Requirement | Why LiteLLM does not cover it |
|-------------|------------------------------|
| Role-based routing | Routes by model name |
| **Global model-lease semaphore** | No equivalent concept |
| Provenance into our schema | Partial, in its own format |
| Schema-constrained output with a repair loop | Partial |
| Local accounting in wall-time and tokens/sec | Cost accounting assumes paid APIs |
| Local-provider parallelism suppression | Not applicable to its model |

## Consequences

**Positive**
- Model choice is configuration. Adding a cloud provider is one new file and a config profile.
- The lease semaphore prevents memory thrash — without it the machine becomes unusable and latency
  numbers become meaningless.
- Complete, uniform provenance for every call, local or cloud.
- One choke point for retries, structured-output repair, accounting and tracing.
- We fully understand the most critical component in the system.

**Negative**
- Code we must write, test and maintain.
- We reimplement things LiteLLM already solved (retry/backoff, some provider quirks).
- Each new provider requires an adapter.
- Risk of gradually growing into a worse LiteLLM if scope is not disciplined.

**Neutral**
- Ties provider support to our own effort, which also means it tracks our actual needs.

## Reversal criteria

- We need to support more than ~4 providers simultaneously.
- We need production features LiteLLM has and we do not: load balancing across endpoints, fallback
  chains, a budget manager, virtual keys.
- Maintenance of provider adapters becomes a recurring drag.

Migration would be contained: LiteLLM would become one `Provider` implementation behind the same
interface, keeping role routing, leasing and accounting on our side. That is a genuinely small change
because the abstraction boundary was drawn deliberately.
