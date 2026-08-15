# Two-minute demo guide

Use only public BPS data already published through the governed pipeline.

| Time | Screen | Talk track |
|---:|---|---|
| 0:00–0:15 | System status | NusaIntel combines a quality control tower, transparent opportunity scoring, and evidence-bound regional analytics. |
| 0:15–0:35 | Control Tower | Show dataset health, freshness, contract version, quality history, lineage, and the absence of open release incidents. |
| 0:35–1:10 | Opportunity Engine | Compare up to five provinces, show explicit directions/weights, run the score, and open contributions plus source/version evidence. |
| 1:10–1:30 | Sensitivity | Explain the Bali/DKI rank reversal from `docs/case-studies.md`; stress that it is not confidence or causality. |
| 1:30–1:50 | Regional analytics | Show the 38-province schematic map, equivalent table, similar regions, cluster evidence, and one source-aware regional detail page. |
| 1:50–2:00 | Methodology and limits | Point to reference periods, immutable dataset versions, no zero-fill, public-data scope, and the non-boundary map disclaimer. |

## Screenshot handoff

The automated E2E suite validates 1440×1000 and 360×800 layouts. The README portfolio set
uses populated local data, meaningful alt text, and no browser chrome or secret values:

1. **Captured:** Opportunity Engine results at a 1874×926 desktop viewport, including
   configuration, ranking, and score contributions.
2. **Captured:** Desktop Control Tower dataset health and quality evidence.
3. **Captured:** Mobile Regional Analytics configuration at a 375×811 rendered viewport.

The optimized assets are stored under `docs/assets/`.
