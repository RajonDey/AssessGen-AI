# ADR-0001 — Immutable content versioning

**Status:** Accepted · **Date:** 2026-07-30

## Context

Assessment content has an unusual durability requirement. A test a student sat in 2026 must be
reproducible exactly in 2030 — for score verification, dispute resolution, or simply to understand a
historical result. Meanwhile the same items get edited, revised by AI, corrected by reviewers and
reused across many tests.

Standard CRUD makes these two requirements contradict each other: editing an item silently changes
every test that used it, including tests students already took.

## Decision

Content identity and content data are separate tables. `items` / `passages` hold stable identity and
a pointer; `item_versions` / `passage_versions` hold immutable, append-only content. Editing appends
a version and moves the pointer. Question sets reference **version IDs**, not item IDs. Publication
produces a fully denormalised, frozen snapshot.

`UPDATE` on a versions table is blocked by a database trigger, not by convention.

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| Mutable rows + audit log | The audit log records *that* something changed, not *what the content was*. Cannot reproduce a historical test |
| Event sourcing | Full reproducibility, but every read needs projection. Complexity is unjustified for a content system with modest write volume |
| Soft delete + `is_current` flag | A partial version of this design with none of the guarantees — nothing prevents in-place edits |
| Postgres temporal tables / `pg_audit` | Ties us to a Postgres-specific mechanism and still permits application-level mutation |

## Consequences

**Positive**
- Historical reproducibility is structural, not procedural.
- Rollback is moving a pointer.
- Prompt-regression detection by diffing versions of the same item.
- The audit trail is the data model, not a parallel system that can drift from it.

**Negative**
- More storage. Acceptable: text is small and disk is cheap.
- Every read needs a version join. Mitigated by `current_version_id` and a denormalised
  `quality_summary` for list views.
- Developers must internalise "never UPDATE". The trigger enforces it, but it will surprise people.
- Bulk edits are more expensive — N edits create N versions.

**Neutral**
- The API surface has no `PATCH` or `DELETE` for content, which makes the guarantee visible to
  clients rather than hidden in the backend.

## Reversal criteria

- Storage growth becomes material (> 100 GB of version data) **and** analysis shows most versions are
  never read. Response would be archiving old versions to cold storage, not abandoning immutability.
- Version-join overhead dominates read latency in profiling and denormalisation cannot fix it.

Neither would justify mutable content. Immutability is load-bearing for the product's core promise;
these would only change *where* old versions live.
