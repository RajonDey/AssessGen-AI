# 11 — Security, Copyright & Compliance

## Part 1 — The copyright firewall

### Why this section exists

You said: *"We can use IELTS practice books and tests to train the product — that's fine, as we will
build our own."*

The intent is right and the method needs care. Here is the problem stated plainly:

**LLMs reproduce their inputs.** If authentic Cambridge passages are placed in prompts as examples for
the model to imitate, or used to fine-tune, then some fraction of "original" output will contain
protected expression — sometimes verbatim, sometimes as close paraphrase. That output then gets
published, sold or licensed under a claim of originality.

The consequence is not a quality issue. It is: takedown demands, contract termination with any B2B
customer, and the destruction of the "original content" claim that is the engine's entire commercial
premise. And the failure is *silent* — you would not know it happened until someone else noticed.

### The distinction that resolves it

Copyright protects **expression**, not **facts, ideas, or systems**. That line is exactly where the
firewall goes:

| ✅ Safe — facts, ideas, structure | ❌ Unsafe — expression |
|---|---|
| "Academic Reading passages average 850 words" | Using a passage as a style example |
| "Papers typically mix 4–6 question types" | Copying a passage's phrasing or structure sentence-by-sentence |
| Distribution of Flesch-Kincaid by band | Fine-tuning on passage text |
| "Answers spread across the whole passage" | Few-shot prompting with real passages |
| Question-type taxonomy and instruction wording (functional) | Reusing a distinctive distractor set |
| Published band descriptors (cite the source) | Reproducing a question stem |

The first column makes our content *better calibrated*. The second column creates liability without
making it better — a well-specified prompt plus a strict rule engine outperforms few-shot imitation
anyway, because the rules enforce what the examples were only implying.

### The firewall design

```
┌──────────────────────────────────────────────────────────────────┐
│  QUARANTINE ZONE — reference_documents                           │
│                                                                  │
│  Authentic third-party material. Encrypted at rest. Gitignored.  │
│                                                                  │
│  Readable by EXACTLY ONE consumer:                               │
│     • the originality checker (negative overlap test)            │
│                                                                  │
│  Readable by NOTHING else. Enforced by:                          │
│     • repository-level access control                            │
│     • an import-linter contract (CI-blocking)                    │
│     • a Cursor rule (blocks AI agents from wiring it in)         │
└──────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
        ┌───────────▼─────────┐   ┌──────▼───────────────────┐
        │ STATISTICS EXTRACT  │   │ ORIGINALITY CHECK        │
        │ (offline, one-off)  │   │ (every generated item)   │
        │                     │   │                          │
        │ Produces NUMBERS:   │   │ 8-gram overlap?          │
        │ word counts, FK     │   │  → QUARANTINE + alert    │
        │ ranges, type mix,   │   │                          │
        │ answer positions    │   │ Corpus text NEVER        │
        │                     │   │ leaves this function     │
        │ Numbers → rules     │   │                          │
        └─────────────────────┘   └──────────────────────────┘
```

The elegance of this design is that **the corpus becomes a safety asset rather than a liability.**
Holding authentic material is what lets us *prove* our output does not overlap with it. Without the
corpus we could only hope; with it, quarantined and used only negatively, we can demonstrate.

### Hard rules

1. `reference_documents` rows MUST NEVER appear in a prompt, few-shot example, or agent context.
2. No fine-tuning on third-party material, ever.
3. Authentic material MUST NOT be committed to git (`evals/calibration/authentic/` is gitignored).
4. Every generated passage MUST pass the 8-gram originality check before reaching `approved`.
5. An originality failure is a **hard block with an operator alert**, never a soft warning.
6. Statistics extraction is a documented offline process producing only aggregate numbers, reviewed
   before those numbers enter the rule engine.

### Our own output

- Generated content is our property, subject to the model provider's terms. Local models
  (Qwen3.5 — Apache 2.0) have no output restrictions, which is a genuine strategic advantage of the
  local-first path and worth weighing in the production model decision.
- We never claim IELTS/Cambridge/IDP/British Council affiliation or endorsement. "IELTS" is used
  descriptively (a practice test *for* IELTS), and trademark attribution appears in the product.
- Published packs carry provenance metadata: generated, machine-checked, human-reviewed, with dates.

---

## Part 2 — Application security

### Threat model

One internal team today, an external consumer API tomorrow. The realistic threats:

| Threat | Impact | Priority |
|--------|--------|----------|
| **Answer keys leak to students** | Destroys every test containing them | **Critical** |
| Unpublished content leaks to a competitor | Loss of IP advantage | High |
| Consumer API key compromise | Content theft at scale | High |
| Cross-tenant data access (post-SaaS) | Contractual and legal breach | High |
| Prompt injection via ingested reference text | Corrupted content, possible data exfiltration | Medium |
| Admin account compromise | Full content control | Medium |

**Answer-key leakage is the top risk and it is structural, not incidental.** A leaked key silently
invalidates every test built on that item, and you find out from score anomalies weeks later.

### Answer key handling

1. The consumer API **omits answer keys by default**. Returning them requires the `content:answers`
   scope, granted per API key.
2. IELTS Ready's client-side code must never receive keys. Grading happens server-side.
3. There is a contract test asserting keys are absent without the scope — it is a build-blocking
   security test, not an afterthought.
4. Key access is logged with key ID, publication ID and timestamp.

### AuthN / AuthZ

**Admin API** — email + Argon2id password → short-lived access JWT (15 min) + refresh token in an
`HttpOnly; Secure; SameSite=Strict` cookie. Role-based permissions checked in a FastAPI dependency,
never inline in handlers. TOTP MFA for `admin` before any external exposure.

**Consumer API** — API keys, stored hashed, prefixed for identification (`agk_live_...`), scoped
(`content:read`, `content:answers`, `publications:list`), independently revocable, with per-key rate
limits.

**Tenant isolation** — every content repository method requires an `organization_id`; the base
repository raises if absent. An integration test asserts an unscoped query fails. When multi-tenancy
goes live, add Postgres row-level security as defence in depth — the application check alone is one
forgotten `WHERE` clause away from a breach.

### Prompt injection

Attack surface is narrow but real: ingested reference documents and operator-supplied topic strings
both reach a model.

- Treat all ingested text as untrusted data, never instructions.
- Structural separation: content goes in dedicated message parts, never concatenated into the system
  prompt.
- Output is schema-constrained, so an injected instruction cannot change the response *shape*.
- `R-PASS-003` catches meta-text ("as an AI", "ignore previous instructions") leaking into content.
- Agents have no tools with side effects. There is no shell, no filesystem write, no arbitrary HTTP.
  An injected instruction has nothing useful to reach.

That last point does most of the work. Prompt injection is dangerous in proportion to agent
capability; our agents only return text.

### Secrets

- `.env` gitignored; `.env.example` committed with dummy values.
- Config read **only** through `pydantic-settings` in `config.py`. No `os.getenv` scattered around.
- Production secrets come from the platform secret store, never a file.
- `gitleaks` in pre-commit and CI.
- Any API keys added later are per-environment, never shared between dev and production.

### Data protection

| Data | Sensitivity | Handling |
|------|------------|----------|
| Generated content (unapproved) | Medium | Internal only |
| Answer keys | **High** | Scope-gated, logged, server-side grading only |
| Reference corpus | **High** (legal) | Encrypted at rest, quarantined, never in git |
| User credentials | High | Argon2id, never logged |
| API keys | High | Stored hashed |
| Prompts | Medium | Business IP; in git, private repo |

**No student PII enters this system.** The engine produces content; IELTS Ready holds student data.
That boundary is a deliberate compliance simplification — it keeps the engine out of GDPR data-subject
scope almost entirely, and it should be defended when future features tempt otherwise.

### Sending content to third-party APIs

If the production model decision favours a hosted provider, that is a **data-handling decision**, not
just a technical one:

- Prompts and generated content go to a third party.
- Verify the provider's data-retention and training-use terms; require zero-retention where possible.
- Reference corpus text must **never** be sent to any external API. The firewall already prevents
  this — it is worth restating because it is the highest-consequence violation available.
- Record the choice and its terms in an ADR.

### Audit trail

The versioned schema already provides most of it. Additionally logged:

- Every authentication attempt, success or failure.
- Every review decision (reviewer, target, decision, timestamp).
- Every publication and revocation.
- Every consumer API key use with answer-key scope.
- Every prompt activation and rollback.

Audit rows are append-only and retained indefinitely.

---

## Compliance checklist before external exposure

Not required for internal Phase 1–2 use; **required** before any third party touches the system:

- [ ] MFA enforced on all `admin` accounts
- [ ] Consumer API keys scoped, hashed, rate-limited and revocable
- [ ] Answer-key scope test passing in CI
- [ ] Row-level security enabled on content tables
- [ ] Originality check passing on 100 % of published content
- [ ] Terms of service clarifying no IELTS affiliation
- [ ] Data-processing terms with any external model provider
- [ ] `gitleaks` clean across full history
- [ ] Dependency audit clean (`pip-audit`, `pnpm audit`)
- [ ] Backup and restore tested, not merely configured
