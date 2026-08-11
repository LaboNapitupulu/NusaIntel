# Regional analytics methodology

- Methodology version: `regional-analytics-v1`
- Preprocessing version: `zscore-complete-case-v1`
- Release: `0.4`

## Comparable feature set

An analysis accepts two to six published indicators and one common analysis year. A feature
is retained only when its share of available observations meets the requested threshold
(0.95 by default). Regions missing any retained feature are then excluded. No mean, median,
carry-forward, or zero imputation is performed.

Retained values are sorted by indicator code and BPS region code. Each value is standardized
as `(x - mean) / population standard deviation`. A constant feature receives scale 1 and
therefore contributes zero standardized variation. Analysis requires at least two retained
features and three complete regions.

The feature-set identifier hashes the analysis year, preprocessing version, ordered feature
list, mean and scale, and each immutable Gold version ID/checksum. This makes configuration
and data changes visible even when the endpoint path is unchanged.

## Similar regions

For target region `a` and candidate `b` over `m` retained features:

```text
distance(a, b) = sqrt(sum((z[a,i] - z[b,i])^2) / m)
```

Lower distance means a more similar standardized profile, not geographic proximity or an
equivalent policy context. Each result reports the squared-distance share per feature,
alongside target/candidate raw values and units. Ties resolve by region code.

## Cluster validation

For every candidate `k`, deterministic k-means is fitted for the configured seeds. Cluster
IDs are canonicalized by centroid order so IDs are stable across equivalent runs. The report
records:

- mean silhouette across seeds;
- mean pairwise adjusted Rand index as stability evidence; and
- minimum cluster membership.

The highest-evidence candidate is selected deterministically. Membership is published only
when mean silhouette and stability meet the request thresholds and no degenerate grouping
invalidates the result. Otherwise assignments and descriptions are empty and the validation
message explains that the result was withheld.

Descriptions summarize the largest positive or negative standardized centroid deviations
using wording such as “relatif lebih tinggi” or “relatif lebih rendah”. They are not ratings,
recommendations, causal claims, or forecasts.

## Map and report

The map is a self-authored schematic tile arrangement of the 38 BPS province codes. Tile
position, size, and adjacency are not administrative geography. Color uses within-report
quantile bands for one selected indicator; a neutral no-data style is separate. Buttons are
keyboard accessible and the complete table is the non-visual equivalent.

The JSON report is the canonical export. It contains configuration, methodology and feature
versions, similarity drivers, cluster validation evidence, map values, exclusions,
limitations, units, source URLs, reference periods, and dataset versions. Browser print
styles produce a compact human-readable report. CSV is intentionally not supported.

## Reproduction checklist

1. Retain the exported configuration and cited Gold versions.
2. Apply coverage and complete-case filtering exactly as recorded.
3. Recalculate ordered means/scales and verify the feature-set hash.
4. Standardize values and calculate RMS Euclidean distances.
5. Fit each candidate `k` for the recorded seeds and calculate silhouette/stability.
6. Apply the recorded publication thresholds before reading any membership.

## Limitations

- Similarity and clustering are descriptive and do not establish causality.
- Standardization gives each retained feature equal scale, not equal policy importance.
- Complete-case analysis can reduce the represented region universe.
- Stability across deterministic seeds is model evidence, not statistical confidence.
- Tile positions are schematic and cannot support boundary, area, or distance analysis.
