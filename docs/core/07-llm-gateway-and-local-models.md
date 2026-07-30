# 07 — LLM Gateway & Local Models

## The decision this document supports

You chose: **build a provider-agnostic gateway, run 100 % local during development, and defer the
production model decision until benchmark data exists.**

That is the right call, but it only works if two things are true from the first commit:

1. **No agent code ever knows which model it is talking to.** Otherwise "swap the model" becomes a
   refactor and the deferral was an illusion.
2. **We measure quality and cost per model from day one.** Otherwise the deferred decision gets made
   later on vibes, which is the same as not deferring it.

Everything below serves those two requirements.

---

## Hardware reality

**Apple M4 · 16 GB unified memory · ~42 GB free disk.** Unified memory means the model competes with
the OS, your IDE, the browser, Docker and Postgres for the same pool.

Realistic budget with a 9 B model resident:

| Consumer | Memory |
|----------|--------|
| macOS + IDE + browser | ~4.5 GB |
| Ollama runtime overhead | ~0.7 GB |
| Qwen3.5 9B Q4_K_M weights | ~6.6 GB |
| KV cache @ 32 K context (q4_0) | ~3.2 GB |
| Postgres + Redis (Docker) | ~0.5 GB |
| FastAPI + Celery worker | ~0.6 GB |
| **Total** | **~16.1 GB** |

That is not "comfortable", it is "exactly at the ceiling". Three consequences are baked into the
architecture rather than left to discipline:

1. **Exactly one large model may be resident at a time.** Enforced by a semaphore in the gateway.
2. **The Next.js dev server does not run during 9 B generation.** Hence the Compose profiles.
3. **Disk budget for models is 15 GB.** Three quantised models, not a collection.

---

## Model roles

Callers request a **role**, never a model. This indirection is the entire mechanism by which the
production decision stays deferred.

| Role | Used by | What it needs | Dev default |
|------|---------|--------------|-------------|
| `generator` | Passage, question, answer generation | Best available quality; long context | `qwen3.5:9b` (Q4_K_M) |
| `critic` | Critic agent | **Must differ from the generator** | `gemma4:12b` or a different prompt+temperature on 9 B |
| `metadata` | Tagging, topic, time estimates | Fast, cheap, structured | `qwen3.5:4b` |
| `embedding` | Dedup, similarity, retrieval | Small, stable | `nomic-embed-text` (768 d) |
| `judge` | Eval harness only | Isolated from production paths | configurable |

> **Why the critic must not be the generator.** A model asked to grade its own output is measuring
> agreement with itself. It reliably rates its own work higher and, worse, is blind to exactly the
> failure modes it just committed — the reasoning that produced the error also endorses it. Using a
> different model family is best; if memory forbids it, a different prompt, a different temperature,
> and **no access to the generation rationale** is the minimum acceptable substitute. The critic sees
> only the finished artefact, exactly as a human reviewer would.

### Model profiles

Switch the whole system with one setting.

| Profile | generator | critic | metadata | When |
|---------|-----------|--------|----------|------|
| `fast` | qwen3.5:4b | qwen3.5:4b (diff. prompt) | qwen3.5:4b | Pipeline development. Content quality irrelevant |
| `local` | qwen3.5:9b | qwen3.5:9b (diff. prompt) | qwen3.5:4b | Default. Real content work on this machine |
| `local-hq` | gemma4:12b | qwen3.5:9b | qwen3.5:4b | Quality experiments. Sequential only, tight |
| `cloud` | *(TBD)* | *(TBD)* | *(TBD)* | Production candidate — chosen from benchmark data |

`fast` exists because most development is about whether the *graph* is correct, not whether the prose
is good. Iterating a workflow bug against a 9 B model at 25 tok/s wastes hours per day.

---

## Gateway design

```
      agents
        │  gateway.complete(role="generator", prompt=..., schema=ItemSchema)
        ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM GATEWAY                            │
│                                                             │
│  1. Resolve role → provider + model (from active profile)   │
│  2. Acquire model lease  ◀── global semaphore, size-aware   │
│  3. Render prompt from versioned template → hash it         │
│  4. Call provider with JSON-schema constraint               │
│  5. Validate against Pydantic schema                        │
│       ├─ fail → repair prompt → retry (max 2)               │
│       └─ ok   → continue                                    │
│  6. Record AgentInvocation: tokens, latency, tok/s, cost,   │
│     seed, params, prompt_hash, model_digest                 │
│  7. Release lease                                           │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
      OllamaProvider │ OpenAIProvider │ AnthropicProvider │ GoogleProvider
```

**Nothing outside `infrastructure/llm/` may import a provider SDK.** Enforced by import-linter.

### The model lease

The single most important piece of infrastructure for this machine.

```python
# Conceptual — the real implementation lives in infrastructure/llm/lease.py
class ModelLease:
    """Bounds resident model memory across all workers on one host.

    Ollama will happily load a second model on request and then swap to disk or
    fail. Both outcomes are much worse than waiting: a swapping Mac becomes
    unusable and the run's latency numbers become meaningless.
    """
    async def acquire(self, model: str, est_memory_gb: float) -> Lease: ...
```

Implemented as a Redis-backed semaphore keyed by total resident GB, with a budget from config
(`LLM_MEMORY_BUDGET_GB=11` on this machine). Requesting a model that would exceed the budget waits
rather than evicting.

Two rules follow, and they are not negotiable on this hardware:

- **`q.generate` runs with concurrency 1.**
- **Parallel fan-out inside a graph is disabled when the provider is local.** The graph may *express*
  parallelism (and will use it against a cloud provider); the gateway serialises it locally. This is a
  configuration flag, not two code paths.

### Structured output

Every generation call is schema-constrained. Ollama supports `response_format: json_schema`, which we
generate directly from the Pydantic model.

Two known traps, handled in `structured.py`:

1. **Reasoning models and schema constraints interact badly.** With thinking enabled, some clients
   apply the JSON schema to the thinking tokens rather than the answer. We disable thinking mode for
   schema-constrained calls, or parse the final block explicitly.
2. **Schema-valid but semantically empty output.** A model under a tight schema will happily emit
   `{"stem": "", "options": []}`. Pydantic validators enforce non-trivial content — minimum lengths,
   required option counts, no placeholder text — so L0 catches this rather than the rule engine.

Failure path: repair prompt including the validation error → retry (max 2) → fail the node with a
`schema_error` invocation recorded. We never silently accept partial output.

### Accounting, including local

Local inference feels free and is not. It costs wall-clock time, machine availability and eventually
hardware. Every call records:

```
input_tokens · output_tokens · latency_ms · tokens_per_second
model_name · model_digest · provider · params(temperature, top_p, seed, num_ctx)
prompt_version_id · prompt_hash · attempt · status
cost_usd            # 0.0 for local, real for cloud
```

`cost_usd` for local runs stays 0, but `latency_ms` accumulates into **machine-hours per approved
item** — the number that actually decides whether a GPU server is worth buying. See
[Observability & Cost](12-observability-and-cost.md).

---

## Setup on this machine

```bash
ollama pull qwen3.5:9b          # ~6.6 GB  — generator (local profile)
ollama pull qwen3.5:4b          # ~3.5 GB  — metadata, fast profile
ollama pull nomic-embed-text    # ~0.3 GB  — embeddings
# Total ~10.4 GB of the 15 GB model disk budget
```

`llama3.2:1b` is already present and is useful for **test suites only** — it is far too weak for
content but makes end-to-end pipeline tests run in seconds.

Recommended Ollama environment:

```bash
OLLAMA_KEEP_ALIVE=15m       # avoid reload thrash between calls in one run
OLLAMA_MAX_LOADED_MODELS=1  # belt and braces alongside our own lease
OLLAMA_NUM_PARALLEL=1
```

---

## ⚠️ The honest assessment of local quality

**A 9 B model at 4-bit quantisation will not reliably produce Band 8 IELTS Academic content.**

State this plainly now, so nobody is surprised in month three. Expect, based on the class of model:

| Task | Realistic local quality |
|------|------------------------|
| Reading passage, 900 words, coherent, on-topic | Good — this is largely fluent prose generation |
| Passage at a *precisely controlled* CEFR/band level | Weak. Needs deterministic post-checks and revision |
| MCQ with genuinely plausible distractors | **Weak.** The classic failure: one obviously-correct option and three implausible ones |
| True/False/Not Given | **Weakest.** The False vs. Not Given distinction requires precise reasoning about what a text does *not* claim |
| Sentence completion with verbatim answers | Good *once the rule engine forces it* — the model drifts, the rule catches it |
| Answer-key correctness | Unreliable unmediated; **reliable when evidence spans are machine-verified** |
| Examiner-grade band judgement | Poor. Do not rely on it |

This is precisely why the architecture front-loads deterministic checking. The rule engine is not
belt-and-braces for a good model; **it is the mechanism that makes a mediocre model useful.** A 9 B
model that drafts and a rule engine that refuses anything malformed can, together, produce content
that neither could produce alone.

### What this implies for the roadmap

- Question types are staged by how machine-checkable they are. Sentence/summary completion first
  (verbatim answers are trivially verifiable), True/False/Not Given last.
- Human review rates start high and fall only as calibration data justifies it.
- The benchmark harness is Phase 1 work, not a nice-to-have — it is how the deferred decision
  eventually gets made with evidence.

---

## The benchmark harness

`evals/benchmarks/` runs an identical task set against any configured model and reports comparable
numbers. This is the artefact that converts "should we buy a server?" from an argument into a table.

**Tasks** (fixed, versioned):
1. Generate an 850–950 word Academic passage on a given topic at a target band.
2. Generate 6 sentence-completion items with verbatim answers from a fixed passage.
3. Generate 6 MCQ items with 4 options from a fixed passage.
4. Generate 6 True/False/Not Given items from a fixed passage.
5. Critique a fixed passage+item set containing **known, deliberately planted defects**.

**Metrics per model:**

| Metric | Source |
|--------|--------|
| Rule-gate pass rate | Deterministic — the trustworthy number |
| Planted-defect detection rate | Task 5 — measures critic usefulness directly |
| False-positive rate on clean content | Task 5 with an undefective set |
| Schema-compliance rate | Gateway L0 |
| Tokens/sec, wall time per item | Gateway accounting |
| Cost per 100 items | Cloud: real. Local: machine-hours |
| Human spot-check score | Small sample, when available |

Task 5 deserves emphasis. It measures the thing we most need and can least otherwise verify: whether
a model can *find* defects. Because the defects are planted by us, ground truth is exact and needs no
examiner. It is the cheapest real evaluation in the whole system.

**The purchase decision rule.** Buy hardware when, and only when:

```
(local model's rule-gate pass rate is within ~10 points of the best cloud model)
AND (projected machine-hours at target volume exceed available capacity)
AND (12-month cloud cost at target volume > hardware cost + running cost)
```

If the local model is far behind on quality, a faster machine does not fix it — that is a model
problem, not a throughput problem, and buying hardware would be solving the wrong bottleneck.

---

## Adding a cloud provider later

Should benchmarks favour a hosted model, the work is intentionally small:

1. `uv add langchain-openai` (or anthropic / google-genai).
2. Add `providers/openai.py` implementing the same `Provider` protocol.
3. Add a `cloud` profile to config.
4. Set real per-token pricing in the cost table.
5. Review [Compliance](11-security-copyright-compliance.md) — sending content to a third party is a
   data-handling decision, not only a technical one.

No agent, workflow, domain, schema or API change. If any of those need to change, the gateway
abstraction has leaked and that is a bug to fix rather than route around.
