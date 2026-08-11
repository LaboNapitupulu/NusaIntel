# ADR 0002: Versioned, allow-listed Control Tower contract engine

- Status: Accepted
- Date: 2026-08-11

## Context

Phase 2 had indicator-specific quality checks embedded in Python. Phase 3 needs auditable
contracts that can be validated before execution, attached to every quality result, and
extended without allowing arbitrary code from a JSON document.

## Decision

NusaIntel uses a strict JSON contract format with two independent version numbers:

- `schema_version` identifies the portable document format (`1.0` initially); and
- `contract_version` is an immutable positive integer scoped to a dataset.

Pydantic validates the runtime representation with `extra="forbid"`. A checked-in JSON
Schema provides a tool-neutral contract at `contracts/dataset-contract.schema.json`.
Contracts support column/type/nullability, composite uniqueness, numeric ranges, accepted
values, freshness, row-count changes, and a small allow-list of custom operators.

Every `QualityCheckResult` references the exact `DataContract` row used. Silver and Gold
MVP datasets each receive a contract. Critical failures block Gold, warnings remain visible,
and a bypass is valid only when a stored exception has a reason, owner, and unexpired time.
Free-form Python, SQL, or expression evaluation in contract documents is prohibited.

## Consequences

- Historical runs remain reproducible when a contract changes.
- Invalid or unknown contract fields fail before pipeline execution.
- Custom validation grows through reviewed operators rather than user-supplied execution.
- Schema drift can be represented consistently as added, removed, type-changed, or
  constraint-changed events.
- Adding a new operator requires backend code and tests, which is intentionally slower but
  safer than arbitrary expressions.
