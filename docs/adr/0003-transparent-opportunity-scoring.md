# ADR 0003: Transparent, version-bound regional opportunity scoring

- Status: Accepted
- Date: 2026-08-11

## Context

Regional indicators use different units, favorable directions, and official reference
months. A useful comparison must make those differences visible, avoid silent imputation,
and let a reviewer reproduce a score from the raw observations and weights. The product
also needs shareable scenarios without collecting user identity.

## Decision

NusaIntel treats a ranking as a user-controlled scenario, not an objective regional fact.
Each request contains two to five provinces, one to six indicators, an analysis year,
explicit favorable direction, weights totalling 100 percent within 0.01, a normalization
method, and a coverage threshold.

The engine supports min-max and percentile-rank normalization on a 0–1 scale. A
lower-is-better indicator is inverted after normalization. Ties receive the same average
percentile and equal final scores receive the same rank. A constant or single-value series
is neutral at 0.5.

Missing observations remain null. A region below the configured coverage threshold is not
scored or ranked. If the threshold permits partial coverage, only available weights are
renormalized and both configured and effective weights are returned. Every response is
bound to immutable Gold version IDs and checksums and exposes raw value, normalized value,
effective weight, contribution, source, and official reference period.

The analysis selector uses a year rather than a fabricated common date. The response keeps
the indicator-specific reference period—for example March poverty and August labour
figures—visible. Sensitivity varies each weight up and down, renormalizes the total, and
reports rank movement; it is explicitly not a confidence interval or causal estimate.

Scenario sharing uses an encoded URL state containing only public region/indicator choices
and method parameters. It stores no user identity. Server-generated JSON exports contain
the full configuration, dataset versions, ranking, sensitivity result, and limitations.

## Consequences

- A score is deterministic for the same version and configuration and can be checked by
  hand.
- Missingness and heterogeneous reference periods cannot disappear behind a single number.
- Adding a normalization method requires an engine change, tests, and a methodology version
  update.
- URL scenarios are portable but are not server-side saved workspaces.
- Rankings remain descriptive and scenario-dependent; they are not forecasts or investment
  recommendations.
