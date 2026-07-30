# 09 — Testing & QA

## Two kinds of quality, kept separate

This project has an unusual property: it has **two independent quality problems**, and confusing them
is a common and expensive mistake.

| | Software quality | Content quality |
|---|---|---|
| Question | Does the code do what we intended? | Is the generated IELTS content good? |
| Method | Tests: unit, integration, contract, E2E | The quality gate + calibration |
| Determinism | Deterministic; same input → same result | Stochastic; same input → different output |
| Where | `backend/tests/`, `admin/tests/` | `evals/`, `domain/quality/` |
| Owner | CI, blocks merge | The eval harness, blocks prompt activation |
| Document | This one | [Quality & Evaluation](08-quality-and-evaluation.md) |

**Never assert on model output in a unit test.** A test like
`assert "photosynthesis" in generated_passage` will fail randomly, get marked flaky, and then get
deleted along with the useful tests around it. Model behaviour is measured by the eval harness with
rates and thresholds, not asserted by pytest with equality.

---

## Test pyramid

```
        ╱╲          E2E (~10)         full run, tiny model, minutes
       ╱──╲         Contract (~30)    OpenAPI conformance, seconds
      ╱────╲        Integration (~80) real Postgres+pgvector, ~1 min
     ╱──────╲       Unit (~500+)      pure functions, < 10 s total
    ╱────────╲
```

The pyramid is bottom-heavy **because the domain layer is pure**. That was an architectural choice
made specifically to buy a fast, deterministic, exhaustive test suite over the code that matters most.

---

## Unit tests — the rule engine above all

The rule engine is where correctness lives, so it gets the most testing effort. Every rule has a test
file with at least four cases:

```python
# tests/unit/modules/ielts/reading/rules/test_R_COMP_001.py

def test_passes_when_answer_is_verbatim_substring(): ...
def test_fails_when_answer_is_paraphrased(): ...
def test_passes_with_different_casing(): ...          # case-insensitive by spec
def test_fails_when_answer_words_are_non_contiguous(): ...
def test_handles_punctuation_and_unicode_normalisation(): ...
def test_returns_offsets_in_detail_for_dashboard_highlighting(): ...
```

That last one matters: `detail` drives the reviewer UI, so it is behaviour, not debug output.

**Property-based tests for invariants** that must hold for all inputs:

```python
@given(passage=passage_strategy(), item=completion_item_strategy())
def test_verbatim_rule_never_raises(passage, item):
    result = R_COMP_001.check(item, passage)
    assert isinstance(result.passed, bool)

@given(text=st.text())
def test_normalisation_is_idempotent(text):
    assert normalise(normalise(text)) == normalise(text)
```

Rules run against untrusted model output containing unicode, emoji, control characters and unbalanced
quotes. A rule that raises is worse than a rule that fails — it takes down the run instead of
rejecting the item.

**Also unit tested:** the lifecycle state machine (every legal and illegal transition), readability
and CEFR helpers against known-value fixtures, and content hashing/normalisation.

## Integration tests

Real Postgres 18 + pgvector via `testcontainers`. No mocked database — the things we most need to
verify (constraints, triggers, transaction semantics, vector search) are exactly the things a mock
would fake.

Priority cases:

```python
def test_updating_an_item_version_raises()               # immutability trigger
def test_approving_with_failing_must_rule_is_rejected()  # gate trigger
def test_version_numbers_are_assigned_monotonically()
def test_publication_snapshot_is_unaffected_by_later_item_edits()   # ★
def test_repository_query_without_org_id_raises()        # tenant scoping
def test_similarity_search_returns_expected_neighbours()
def test_idempotency_key_conflict_returns_original_run()
```

The publication-snapshot test is the most valuable integration test in the suite. It verifies the core
promise of the data model — that a published test is genuinely frozen — and it is the kind of
guarantee that silently breaks during an unrelated refactor.

**Migration tests:** every migration is applied to a seeded database and verified to preserve data and
immutability triggers. `alembic upgrade head` from empty runs in CI on every commit.

## Contract tests

The OpenAPI schema is the contract with the dashboard and with IELTS Ready.

- Schema is generated and diffed in CI; a breaking change without a version bump fails the build.
- The generated TypeScript client is regenerated and compared; a stale checked-in client fails.
- Error responses are validated against RFC 9457.
- Consumer API responses are asserted to **never** include answer keys without the `content:answers`
  scope. This is a security test as much as a contract test.

## E2E tests

Few, slow, high value. Run against `llama3.2:1b` — already installed, far too weak for real content
but perfect for exercising the pipeline in seconds.

```
test_full_reading_run_reaches_awaiting_review
test_run_survives_worker_restart_and_resumes_from_checkpoint   ★
test_human_approval_via_api_resumes_the_paused_graph
test_must_rule_failure_blocks_and_does_not_persist_as_approved
test_export_produces_a_valid_pdf
```

The restart test is the one that catches the most dangerous class of bug. It kills the worker
mid-run and asserts the run resumes from its last checkpoint with the same `thread_id`. Durable
execution that has never been tested by an actual restart is durable by assumption.

Frontend E2E with Playwright covers the review workflow specifically — claim next item, see findings
inline, approve by keyboard, verify state transition.

---

## The eval harness (content quality)

Lives in `evals/`, run by `make bench` and in CI on prompt changes. Fully described in
[Quality & Evaluation](08-quality-and-evaluation.md); the mechanics:

```
evals/harness/
├── runner.py       execute a task set against a model profile
├── scorers.py      rule-gate pass rate, planted-defect recall, schema compliance
├── compare.py      diff two runs (prompt v2 vs v3; model A vs B)
└── report.py       markdown + JSON output
```

**Gates enforced in CI:**

| Change | Gate |
|--------|------|
| Prompt version activation | Golden-set pass rate must not regress > 5 points |
| New/changed rule | False-positive rate on authentic material ≤ 5 % |
| Model profile change | Benchmark suite runs; results recorded, human decision required |

Because generation is stochastic, gates are **statistical**: n ≥ 30 samples per task, and comparisons
use confidence intervals rather than single-run differences. A single run proving a prompt "better" is
noise.

---

## Static analysis

| Tool | Scope | Enforcement |
|------|-------|-------------|
| `ruff check` + `ruff format` | All Python | Blocks merge |
| `mypy --strict` | `domain/`, `modules/` | Blocks merge |
| `mypy` (normal) | Everything else | Blocks merge |
| `import-linter` | Layer contract | **Blocks merge** |
| `tsc --noEmit`, ESLint | Admin | Blocks merge |

### The layer contract

This is what keeps the architecture real rather than aspirational:

```ini
[importlinter:contract:layers]
name = Architectural layers
type = layers
layers =
    app.api
    app.services
    app.workflows
    app.agents
    app.domain
    app.infrastructure

[importlinter:contract:domain-purity]
name = Domain layer performs no I/O
type = forbidden
source_modules = app.domain
forbidden_modules = app.infrastructure, sqlalchemy, httpx, redis, celery, langchain, langgraph

[importlinter:contract:gateway-monopoly]
name = Only the gateway imports provider SDKs
type = forbidden
source_modules = app.agents, app.workflows, app.services, app.domain, app.api
forbidden_modules = langchain_ollama, langchain_openai, langchain_anthropic, openai, anthropic

[importlinter:contract:reference-corpus-quarantine]
name = Reference corpus is reachable only by the originality checker
type = forbidden
source_modules = app.agents, app.workflows, app.modules
forbidden_modules = app.infrastructure.db.repositories.reference_documents
```

The last two contracts are notable: they enforce in CI what would otherwise be a written policy
nobody remembers. The gateway monopoly is what makes the deferred model decision real. The corpus
quarantine is what makes the copyright firewall a mechanism rather than a promise.

---

## CI pipeline

```
on push / PR
├── lint            ruff, mypy, import-linter, tsc          ~1 min
├── unit            pytest tests/unit                        ~30 s
├── integration     testcontainers Postgres+pgvector         ~3 min
├── contract        OpenAPI diff + client freshness          ~1 min
├── migrations      upgrade head from empty + data checks    ~2 min
└── frontend        vitest + build                           ~2 min

on PR touching prompts/ or rules/
└── evals           golden set + planted-defect suite       ~10 min

nightly
├── e2e             full pipeline with llama3.2:1b
├── calibrate       rule engine vs authentic material
└── bench           model benchmark suite
```

Everything on the fast path stays under ~10 minutes. Evals only run when prompts or rules change,
because they are slow and only meaningful for those changes.

---

## Coverage targets

Coverage is a diagnostic, not a goal — but these thresholds are enforced because low coverage in these
specific places has a known, expensive failure mode:

| Area | Target | Why |
|------|--------|-----|
| `domain/quality/` (rules) | **95 %** | The correctness core. Untested rules give false confidence |
| `domain/` (rest) | 90 % | Pure and cheap to test; no excuse |
| `services/` | 80 % | Transaction boundaries |
| `agents/` | 60 % | Mostly prompt assembly; behaviour is measured by evals |
| `api/` | 75 % | Covered largely by contract tests |
| `infrastructure/` | 60 % | Thin adapters |

Deliberately low for `agents/`: their real behaviour is model behaviour, which the eval harness
measures properly. Chasing coverage there produces tests that assert prompt strings — which break on
every prompt edit and verify nothing.

---

## Minimum QA for Phase 1

If time is short, this is the irreducible set. It is small on purpose:

1. Every implemented rule has unit tests including at least one failing case.
2. The immutability trigger has an integration test.
3. The approval-blocking trigger has an integration test.
4. One E2E test proving a full Reading run reaches `awaiting_review`.
5. `import-linter` runs in CI from the first commit — retrofitting a layer contract onto violated code
   is far more expensive than never violating it.
6. `make calibrate` runs against at least two authentic papers before any rule is allowed to block.

Item 6 is the one most likely to be skipped and least advisable to skip: a rule engine that has never
been checked against real IELTS content is a confident source of false rejections.
