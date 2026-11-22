# 12 — Observability & Cost

## What this instrumentation is for

Not dashboards for their own sake. Three specific questions must be answerable with data:

1. **Is content quality improving or regressing?** — otherwise prompt work is guesswork.
2. **Where does the time and money actually go?** — otherwise optimisation targets the wrong thing.
3. **Should we buy a GPU server?** — the deferred decision from
   [LLM Gateway](07-llm-gateway-and-local-models.md), which only becomes answerable if we start
   measuring before we have an opinion.

Everything below serves one of those three.

---

## Logging

`structlog` emitting JSON. Every log line carries correlation context, bound once at the entry point
and inherited automatically:

```json
{
  "timestamp": "2026-07-30T12:34:56.789Z",
  "level": "info",
  "event": "agent.invocation.completed",
  "request_id": "req_01J2X...",
  "run_id": "018f3a...",
  "organization_id": "018e00...",
  "agent": "question_generator",
  "model": "qwen3.5:9b",
  "prompt_version": "reading.questions.mcq@v3",
  "input_tokens": 2841,
  "output_tokens": 612,
  "latency_ms": 24180,
  "tokens_per_second": 25.3,
  "attempt": 1
}
```

**`run_id` is the join key for everything.** Given a run ID you can reconstruct every model call, every
quality check, every state transition and every review decision. That is the practical form of the
provenance guarantee in [Data Model](04-data-model.md).

**Never logged:** answer keys, passwords, API keys, reference corpus text. A redaction processor in
the structlog chain strips known-sensitive fields rather than relying on call-site discipline.

### Event taxonomy

```
run.created · run.started · run.step.completed · run.paused_for_review
run.resumed · run.completed · run.failed · run.cancelled

agent.invocation.started · agent.invocation.completed
agent.invocation.schema_error · agent.invocation.retry

quality.gate.started · quality.rule.failed · quality.originality.blocked
quality.duplicate.detected · quality.critic.findings

review.claimed · review.decided
publication.created · publication.revoked

llm.lease.acquired · llm.lease.waited · llm.lease.timeout
```

`llm.lease.waited` is worth watching closely on this machine — sustained waiting means the model lease
is the throughput bottleneck, which is exactly the evidence the hardware decision needs.

---

## Tracing

OpenTelemetry, auto-instrumenting FastAPI and SQLAlchemy, with manual spans over the parts that
matter:

```
run.reading                                        (root, ~7 min)
├── plan                                     12 s
├── passage.generate                         84 s
│   └── llm.call  qwen3.5:9b                 81 s   ← where time actually goes
├── quality.gate.passage                    0.4 s
│   ├── rules.R-PASS-001 … 009            0.002 s
│   └── originality.check                   0.3 s
├── questions.generate  (×4 types)          186 s
├── answers.generate                         71 s
├── quality.gate.items                      1.2 s
├── critic                                   96 s   ← second-biggest cost
├── revision.loop  (×1)                     112 s
└── persist + embed                          3 s
```

Two facts fall out of a trace like this immediately: model calls dominate wall time by three orders of
magnitude over rule checks, and the critic is a large fraction of it. That is the argument for
"deterministic checks first" made in numbers rather than principle — and it is why the critic runs
last, on already-filtered content.

LangSmith is wired in optionally for LLM-specific tracing (prompt, completion, token detail). It is
self-hostable; it is not a hard dependency and the system runs fully without it.

---

## Metrics

Prometheus format at `/metrics`.

### Business metrics — the ones that matter

```
assessgen_items_generated_total{module,item_type,model,prompt_version}
assessgen_items_approved_total{module,item_type}
assessgen_items_rejected_total{module,item_type,reason_code}
assessgen_quality_rule_failures_total{rule_code,severity,module}
assessgen_review_seconds_sum{reviewer,module}
assessgen_originality_blocks_total{source}
assessgen_duplicates_detected_total{module}
```

### Derived — computed in the reports layer

```
approval_rate            = approved / submitted_to_review
rule_gate_pass_rate      = passed_all_must / generated
reviewer_minutes_per_item = review_seconds_sum / approved
revision_loops_per_item  = revision_count / approved
cost_per_approved_item   = total_cost / approved            # cloud
machine_hours_per_item   = total_latency / approved         # local
```

### Technical metrics

```
assessgen_llm_invocations_total{provider,model,role,status}
assessgen_llm_latency_seconds{provider,model,role}          # histogram
assessgen_llm_tokens_total{provider,model,direction}
assessgen_llm_lease_wait_seconds                            # histogram
assessgen_run_duration_seconds{module,status}               # histogram
assessgen_queue_depth{queue}
assessgen_runs_awaiting_review                              # stale queue detection
```

---

## Cost accounting

### The local-inference trap

Local inference *feels* free and is not. It consumes wall-clock time and machine availability, and at
sufficient volume it consumes hardware. A system that records `cost = 0` for local runs cannot
answer the hardware question, which is the whole reason the model decision was deferred.

So every invocation records **both**:

```python
cost_usd        # real money. 0.0 for local, provider pricing for cloud.
latency_ms      # wall time. The real currency of local inference.
```

and the reports layer derives machine-hours per approved item alongside dollars per approved item.

### Comparable cost model

To compare local against cloud honestly, local time is priced at a machine rate:

```
LOCAL_MACHINE_COST_PER_HOUR = 0.35   # configurable; amortised hardware + power + opportunity

local_equivalent_cost = (total_latency_ms / 3_600_000) * LOCAL_MACHINE_COST_PER_HOUR
```

This number is an estimate and is explicitly labelled as one in the UI. Its purpose is not accounting
precision — it is to put local and cloud on the same axis so the comparison is possible at all. Its
sensitivity to the assumed rate is shown alongside it.

### The report that decides the hardware purchase

```
Cost analysis · Reading · last 30 days

Model            Items  Approved  Approval  Wall time  Machine-h/item  Est. $/item
qwen3.5:9b (loc)   412       214    51.9 %     18.4 h          0.086       $0.030
qwen3.5:4b (loc)   380       112    29.5 %      6.2 h          0.055       $0.019
<cloud model>      TBD       TBD       TBD        TBD            TBD          TBD

Throughput ceiling on current hardware: ~28 approved items/day (single model lease)
Target volume: 200 approved items/day
Shortfall: 7.1×
```

That last block is the decision. It says plainly: this machine cannot reach the target volume, and the
gap is a factor of seven, not a factor of 1.2. Now the question "buy hardware or use an API" has a
number attached and can be answered rather than debated.

Crucially, it also distinguishes the two failure modes. If the local approval rate is 52 % against a
cloud model's 85 %, **faster hardware does not fix that** — it is a model-capability problem, and
buying a GPU would be optimising the wrong bottleneck at real expense.

---

## Dashboards

### Operations
Runs in flight, queue depths, model lease utilisation and wait time, error rate by type, stale review
queue age.

### Content quality
Approval rate over time **annotated with prompt-version changes** — this single view answers "did that
prompt change help?" better than any other artefact in the system. Plus rule-failure Pareto, rejection
reason-code Pareto, coverage heatmap (topic × band × type), and calibration false-positive rate.

### Cost & throughput
Cost and machine-hours per approved item over time, model comparison, throughput ceiling vs target,
and reviewer minutes per approved item.

---

## Alerts

Only for things a human must act on. Alerts that fire routinely get ignored, and then the one that
mattered gets ignored too.

| Alert | Condition | Severity |
|-------|-----------|----------|
| **Originality block** | Any 8-gram match with reference corpus | **Critical** — page immediately |
| Approval rate collapse | Below 40 % over 50 items | High |
| Rule engine false-positive spike | Calibration above 10 % | High |
| Run failure rate | Above 25 % over 1 hour | High |
| Model unreachable | Health check fails 3× | High |
| Stale review queue | Items awaiting review > 7 days | Medium |
| Lease saturation | Mean wait > 60 s sustained | Medium |
| Disk pressure | Model disk above 90 % | Medium |

The originality alert is the only one that pages. Everything else can wait for working hours; a
copyright incident cannot, because the remedy (stop publishing, quarantine, audit what already
shipped) gets more expensive by the hour.

---

## In-process call ledger (current)

`backend/app/content/cost_ledger.py` counts planner, generator, and critic calls per module for a single worker. It does not store tokens or dollars. Read it at `GET /api/v1/generate/cost-stats`; clear it with `POST /api/v1/generate/cost-stats/reset`. The durable `agent_invocations` ledger described above is still the target for production accounting.

---

## Phasing

Observability is built incrementally, but the parts that must exist from the first generation run are
non-negotiable, because retrofitting them means losing the data from the period you most want to
learn from.

| Phase | Deliverable |
|-------|-------------|
| **1** | structlog JSON; `agent_invocations` fully populated; `quality_checks` recorded; basic reports endpoint |
| **2** | Prometheus metrics; quality dashboard with prompt-version annotations; cost report |
| **3** | OpenTelemetry tracing; alerting; LangSmith integration |
| **4** | Per-tenant usage metering and billing hooks |

**`agent_invocations` must be complete from run #1.** It is the ledger the hardware decision depends
on, and unlike a dashboard it cannot be backfilled.
