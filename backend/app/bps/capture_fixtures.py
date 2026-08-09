from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.bps.client import BPSClient
from app.config import get_settings
from app.pipeline.contracts import CONTRACTS

FILENAMES = {
    "tpak": "tpak_august_2396_2023_2025_live.json",
    "poverty_rate": "poverty_march_total_192_2023_2025_live.json",
    "grdp_per_capita_current": "grdp_per_capita_current_288_2023_2025_live.json",
    "grdp_growth_constant_2010": "grdp_growth_constant_2010_291_2023_2025_live.json",
    "hdi": "hdi_new_method_494_2023_2024_live.json",
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture credential-safe BPS fixtures.")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _write_new_fixture(destination: Path, body: bytes) -> None:
    with destination.open("xb") as fixture_file:
        fixture_file.write(body)


async def _capture(output_dir: Path) -> list[dict[str, str | int]]:
    settings = get_settings()
    if settings.bps_api_key is None:
        raise RuntimeError("BPS_API_KEY is required.")
    credential = settings.bps_api_key.get_secret_value()
    manifest: list[dict[str, str | int]] = []
    async with BPSClient(settings) as client:
        for indicator, filename in FILENAMES.items():
            destination = output_dir / filename
            retrieved = await client.fetch(CONTRACTS[indicator])
            if credential in retrieved.body_text:
                raise RuntimeError(f"Credential found in response body for {indicator}.")
            await asyncio.to_thread(
                _write_new_fixture,
                destination,
                retrieved.body_text.encode("utf-8"),
            )
            manifest.append(
                {
                    "indicator": indicator,
                    "filename": filename,
                    "sha256": retrieved.checksum,
                    "raw_observations": retrieved.row_count,
                }
            )
    return manifest


def main() -> None:
    arguments = _arguments()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = asyncio.run(_capture(arguments.output_dir))
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
