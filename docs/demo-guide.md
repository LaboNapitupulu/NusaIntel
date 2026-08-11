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

The automated E2E suite already validates 1440×1000 and 360×800 layouts. For README
portfolio images, capture the populated local app manually because the controlled browser
environment blocks localhost URLs:

1. Desktop 1440×1000: Opportunity results with contribution and sensitivity panels.
2. Desktop 1440×1000: Control Tower dataset health and quality evidence.
3. Mobile 360×800: Regional analytics map/table and source-aware detail navigation.
4. Save the optimized images under `docs/assets/`, add meaningful alt text in README, and
   avoid including API keys, environment values, or browser chrome.
