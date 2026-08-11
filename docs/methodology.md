# Regional Opportunity Engine methodology

Methodology version: `opportunity-score-v1`  
Release: `0.3`  
Status: Phase 4 baseline

## Scenario inputs

A scenario compares two to five active provinces and one to six published MVP indicators.
The user selects an analysis year, normalization method, favorable direction, indicator
weights, minimum data coverage, and sensitivity perturbation. Weights must total 100
percent within 0.01 percentage point.

The analysis year groups observations for comparison but does not overwrite their official
reference periods. Each raw value and dataset version retains its actual period. Indicators
with no published observation in the requested year are rejected rather than substituted
from another year.

## Normalization and score

For min-max normalization, a value `x` becomes `(x - min) / (max - min)` across available
MVP provinces. For lower-is-better indicators, the result is inverted as `1 - normalized`.
A constant series is assigned the neutral value 0.5.

Percentile normalization orders available values, maps ranks to 0–1, and assigns tied
values their average rank. A single available value is neutral at 0.5. Lower-is-better
percentiles are inverted.

For an eligible region:

```text
score = sum(normalized value × effective weight)
```

Weights are represented as percentages, so the score is on a 0–100 scale. Each contribution
is returned separately. Equal scores share a rank; the engine does not invent precision to
break a tie.

## Missing data and coverage

Missing is always `null`, never zero. Coverage is the share of selected indicators with an
available value. A region below the user-selected threshold has `score = null`, `rank =
null`, and is labelled ineligible. If partial coverage is allowed, weights of available
indicators are transparently renormalized to 100 percent; configured and effective weights
remain visible.

## Compatibility and provenance

An indicator is accepted only when its observed unit matches its catalog unit. Every result
contains the immutable Gold dataset version, checksum, retrieval/source timestamps, actual
analysis reference period, official source URL, and methodology version. Trend rows retain
their own dates and units.

## Sensitivity

For each selected indicator the engine creates a decreased-weight and increased-weight
scenario using the chosen relative perturbation, then renormalizes all weights to 100
percent. It reports the minimum and maximum rank, largest absolute shift, and percentage of
scenarios in which the base rank is unchanged.

Sensitivity describes response to assumptions. It is not statistical confidence,
uncertainty in source data, a forecast, or evidence of causality.

## Reproduction checklist

1. Record the exported configuration and dataset version IDs.
2. Normalize each raw indicator value with the selected method and direction.
3. Confirm coverage meets the threshold.
4. Multiply normalized values by their effective percentage weights.
5. Sum contributions and round to six decimal places.
6. Sort eligible scores descending; assign equal scores the same rank.

The JSON export is the canonical portable evidence package for this baseline.
