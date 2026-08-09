# BPS fixtures

## `dynamic_data_documentation_sample.json`

This fixture mirrors the JSON envelope documented in the official BPS Dynamic Data API documentation:

<https://webapi.bps.go.id/documentation/>

It is intentionally:

- Free of API keys and user identifiers.
- Small enough for deterministic offline tests.
- Limited to envelope/parser discovery.
- Not used as evidence for the six selected MVP indicator values.

The fixture is **documentation-derived**, not a captured authenticated response. Labels and structure follow the official example, while notes and the reduced `datacontent` are sanitized for repository use.

Live-fixture workflow:

1. Make an authenticated request from a local script.
2. Persist the response body only, not the full URL containing `key`.
3. Record endpoint parameters without the key in adjacent metadata.
4. Confirm the payload contains no credential or personal information.
5. Add a checksum and parser regression test.

## Authenticated live fixtures

Captured on 2026-08-08. These files contain response bodies only. API keys and
full authenticated request URLs are not stored.

| Fixture | Request parameters excluding `key` | Purpose | SHA-256 |
|---|---|---|---|
| `domain_provinces_live.json` | `type=prov` | Confirms authenticated access and the 34 BPS province-domain websites | `213e21c6a49908f745e09e2d74857cb8e2bcafc5d084501e8f5a008960367320` |
| `tpt_periods_543_live.json` | `model=th`, `domain=0000`, `var=543` | Resolves year IDs; the captured first page includes 2023–2025 | `8ab1c6d15b588aa7730a1fbbfcabde55d27e00713eed19eeb947fd188121fcae` |
| `tpt_subperiods_543_2023_2025_live.json` | `model=turth`, `domain=0000`, `var=543`, `th=123;124;125` | Resolves February, August, and annual derived-period IDs | `727e9dee318ef080825fe4beb3acc2215c07bf57c15ebb8fbe5effdb9e29d690` |
| `tpt_annual_543_2023_2025_live.json` | `model=data`, `domain=0000`, `var=543`, `th=123;124;125`, `turth=191` | Preserves the valid `list-not-available` annual response | `bda58e487d4888d6268844d0c05f34103eb93b0a812780ce5242a4a7d797721b` |
| `tpt_august_543_2023_2025_live.json` | `model=data`, `domain=0000`, `var=543`, `th=123;124;125`, `turth=190` | Primary Phase 0 live data fixture | `fe66566debdf82e1336cb2d6a22ee0c1e6ffa0b306d560f95cb110822cabcf22` |

The TPT fixture contains 113 of 117 possible geography-year cells: all 38
provinces plus Indonesia for 2024 and 2025, but the four new Papua provinces
have no separate 2023 observation. Missing cells are preserved as missing and
must never be converted to zero.

## `missing_key_error.json`

This is the unchanged response body from a live request to:

```text
GET https://webapi.bps.go.id/v1/api/domain?type=prov
```

made without a `key` parameter on 2026-08-08. It proves that the endpoint is reachable and that BPS enforces key-based authentication. It contains no credential.
