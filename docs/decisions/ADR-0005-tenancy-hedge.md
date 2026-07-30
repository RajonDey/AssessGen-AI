# ADR-0005 — `organization_id` from day one

**Status:** Accepted · **Date:** 2026-07-30

## Context

The engine is internal today — one team, one implicit tenant. The stated future direction is to sell
question packs or API access, and eventually to run a multi-tenant SaaS (Phase 4). When asked, the
decision was that multi-tenancy can be planned later, once the product is ready.

The engineering question is narrower than the product question: **what does it cost to add tenant
scoping later, versus now?**

- **Now:** one column on ~10 tables, a base repository that requires it, one seeded row. Perhaps half
  a day, mostly at the start when there is no data.
- **Later:** backfill every content table with real data in it; audit every query in the codebase for
  a missing `WHERE`; retrofit authorization; and carry the risk that one missed query becomes a
  cross-tenant data leak — the highest-severity bug class a B2B product can ship.

The costs are wildly asymmetric, and the asymmetry grows with every row added.

## Decision

Include `organization_id` on all content tables from the first migration, with a single seeded
`internal` organization. All content repositories require it; the base repository raises if it is
absent, and an integration test asserts that.

**Do not build** organisation management UI, roles beyond a simple enum, billing, per-tenant
configuration, or row-level security. Those are Phase 4 and are not implied by the column.

This is a deliberate separation between the **data-model hedge** (cheap now, expensive later) and the
**product features** (expensive now, appropriately deferred).

## Alternatives considered

| Option | Why rejected |
|--------|--------------|
| No tenancy until Phase 4 | Backfill + full query audit against live data. The one-missed-query risk is a data-leak class bug |
| Full multi-tenant SaaS now | Weeks of work on features with no user. Genuine premature building |
| Separate database per tenant | Operationally heavy; no benefit at one tenant; migrations multiply |
| Schema-per-tenant | Same objection, plus awkward cross-tenant analytics |

## Consequences

**Positive**
- Phase 4 becomes a feature project, not a migration project.
- Queries are written correctly from the start; the pattern never has to be retrofitted into muscle
  memory.
- Cross-tenant leakage is structurally prevented before there is anything to leak.

**Negative**
- Slight ceremony in every repository method for a benefit that is invisible today.
- An unused column and index for possibly a long time.
- Mild risk of over-abstracting toward multi-tenancy in places where it is not warranted.

**Neutral**
- The API does not expose organisations yet; scoping is derived from the authenticated user.

## Reversal criteria

Effectively none — the cost is already sunk once the first migration ships, and removing the column
later would be pure churn.

The genuine open question is not *whether* to carry the column but *when* to build the Phase 4
features on top of it. That is a product decision driven by external demand, tracked as Q9 in
[Open Questions](../execution/open-questions.md).
