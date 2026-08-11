# ADR 0004: Versioned regional analytics and a schematic province map

- Status: Accepted
- Date: 2026-08-11

## Context

Similarity and clustering can make regional patterns easier to explore, but they can also
hide preprocessing choices, overstate weak group structure, or turn descriptive groupings
into normative labels. Geographic presentation adds a separate provenance problem: the
current 38-province product scope needs a redistribution-safe boundary source with matching
administrative coverage.

The geoBoundaries `gbOpen` Indonesia ADM1 release currently represents 2017 and contains
34 units, so it does not match the product universe. The Ministry of Agriculture ArcGIS
layer exposes 38 provincial features, but its public service metadata does not state an
explicit redistribution license. Shipping either artifact would therefore create a scope
or licensing ambiguity.

## Decision

Analytics use complete-case z-score preprocessing. Features below the configured coverage
threshold are excluded, remaining regions with any missing selected value are excluded,
and missing values are never zero-filled. The sorted feature/region universe, means, scales,
Gold version IDs, checksums, year, and preprocessing identifier are hashed into a feature-set
version.

Similarity is root-mean-square Euclidean distance in standardized feature space. Results
include each feature's raw values, standardized gap, direction, and share of squared
distance. Sorting is deterministic by distance and BPS region code.

Clustering compares requested candidate `k` values using deterministic k-means across
multiple seeds. Selection evidence includes mean silhouette, adjusted-Rand stability, and
minimum cluster size. Assignments are withheld when the configured silhouette or stability
threshold is not met. Generated descriptions only state relative standardized deviations;
they do not use labels such as best, worst, advanced, or lagging.

The web product uses a self-authored, keyboard-operable 38-province tile layout. It is
explicitly described as schematic, has no administrative geometry, includes a quantile
legend and no-data style, and is paired with a table containing the same values. No external
boundary data is redistributed. A future authoritative choropleth requires a documented,
compatible 38-province source and license review.

Exports use JSON only. Every displayed/exported measure retains unit, official source URL,
reference period, and immutable dataset version. CSV formula-injection risk is therefore
not introduced in this phase.

## Consequences

- Fixed version and configuration produce repeatable similarity and cluster evidence.
- Weak cluster structure is visible as a withheld result rather than a forced narrative.
- The map supports overview and selection but must not be used for distance, area, or
  boundary interpretation.
- A region can be absent from an analysis because of complete-case rules; exclusions remain
  explicit in the response.
- Boundary-source evaluation must be repeated before replacing the schematic representation.

## Source review

- [geoBoundaries API and licensing metadata](https://www.geoboundaries.org/api.html)
- [Ministry of Agriculture 38-province ArcGIS layer](https://geoportal.pertanian.go.id/arcgis/rest/services/Hosted/Batas_Administrasi_Provinsi/FeatureServer/layers)
