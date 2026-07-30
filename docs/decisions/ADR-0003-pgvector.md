# ADR-0003 — pgvector instead of a dedicated vector database

**Status:** Accepted · **Date:** 2026-07-30

## Context

We need vector similarity for duplicate detection (is this item too close to an existing one?) and,
later, retrieval. Expected scale is modest: tens of thousands of items now, perhaps a few hundred
thousand at maturity. Well within what a general-purpose database handles.

Crucially, the vector must stay consistent with the content it describes. An item version is
immutable, so its embedding should be created in the same transaction and never drift from it.

## Decision

pgvector 0.8.6 in the same PostgreSQL 18 instance as content, with HNSW indexing. Docker image
`pgvector/pgvector:pg18`.

Embedding model name is stored on every row so a mixed-model state is detectable rather than silently
corrupting similarity results.

## Alternatives considered

| Option | Pros | Cons | Why rejected |
|--------|------|------|--------------|
| **Pinecone** | Managed, scales | External service, per-vector cost, network hop, sync problem | Conflicts with the no-API-cost constraint; adds a consistency problem we do not have |
| **Qdrant / Weaviate** | Excellent filtering, fast | Another service to run, back up and keep in sync | On a 16 GB dev machine, another stateful service is a real cost |
| **Chroma** | Simple, embeddable | Weak operational story at scale | Would need replacing later |
| **FAISS** | Fastest, in-process | No persistence, no filtering, no transactions | Would require building a storage layer around it |

## Consequences

**Positive**
- **No synchronisation problem.** Embedding and content are written in one transaction. This is the
  main reason for the decision — a separate vector store means embeddings can outlive deleted content
  or lag behind edits, and the resulting bugs are subtle.
- Vector search joins directly against content filters (`module`, `band`, `status`) in one SQL query.
  Pre-filtering by tenant and status before the vector scan is both correct and fast.
- One database to back up, migrate and monitor.
- No extra memory on a machine that has none to spare.

**Negative**
- Slower than a specialised store at very large scale — irrelevant at ours.
- HNSW index build is memory-hungry; index parameters need tuning as the bank grows.
- Changing embedding dimensions requires a migration and a re-embed backfill.
- Vector operations compete with transactional load on the same instance.

**Neutral**
- Ties us to Postgres — which we are tied to anyway for everything else.

## Reversal criteria

- Item count exceeds ~5 million **and** similarity query latency exceeds ~200 ms after index tuning.
- Vector workload measurably degrades transactional performance and read replicas do not resolve it.
- A requirement emerges for multi-vector or hybrid search that pgvector cannot serve.

At that point the migration is contained: `infrastructure/vector/` is a small module behind an
interface, so swapping the backend does not touch domain or agent code.
