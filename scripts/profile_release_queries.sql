\pset pager off
\timing on

\echo 'Regional latest-observation view'
EXPLAIN (ANALYZE, BUFFERS)
SELECT region_code, indicator_code, period, value
FROM gold.latest_regional_observations
WHERE indicator_code IN ('tpt', 'tpak', 'poverty')
ORDER BY indicator_code, region_code, period;

\echo 'Opportunity Engine observation slice'
EXPLAIN (ANALYZE, BUFFERS)
WITH latest_version AS (
    SELECT dv.id
    FROM ops.dataset_versions AS dv
    JOIN ops.datasets AS d ON d.id = dv.dataset_id
    WHERE d.code = 'tpt_gold'
      AND dv.status = 'published'
    ORDER BY dv.processed_at DESC NULLS LAST, dv.retrieved_at DESC
    LIMIT 1
)
SELECT region_code, period, value, unit
FROM gold.regional_observations
WHERE dataset_version_id = (SELECT id FROM latest_version)
  AND period BETWEEN DATE '2025-01-01' AND DATE '2025-12-31'
  AND is_national_aggregate IS FALSE;

\echo 'Control Tower quality-result history'
EXPLAIN (ANALYZE, BUFFERS)
SELECT q.id, q.check_code, q.severity, q.status, q.created_at
FROM ops.quality_check_results AS q
JOIN ops.dataset_versions AS dv ON dv.id = q.dataset_version_id
JOIN ops.datasets AS d ON d.id = dv.dataset_id
WHERE d.code = 'tpt_gold'
ORDER BY q.created_at DESC
LIMIT 100;
