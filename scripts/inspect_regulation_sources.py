from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.regulasilens.ingestion import fetch_regulation
from app.regulasilens.manifest import load_manifest
from app.regulasilens.parser import extract_pdf_pages, parse_regulation_pages


async def inspect_sources(manifest_path: Path, *, sample_headings: int = 0) -> int:
    manifest = load_manifest(manifest_path)
    failed = False
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {"User-Agent": "NusaIntel/0.5 governed-corpus-verification"}
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        for document in manifest.documents:
            fetched = await fetch_regulation(document, client=client)
            if fetched.status != "accepted" or fetched.body is None:
                failed = True
                print(
                    f"{document.document_id}: {fetched.status} reason={fetched.reason}"
                )
                continue
            parsed = parse_regulation_pages(
                document.document_id,
                extract_pdf_pages(fetched.body),
            )
            pasal_count = sum(section.kind == "pasal" for section in parsed.sections)
            print(
                f"{document.document_id}: accepted bytes={fetched.byte_count} "
                f"sections={len(parsed.sections)} pasal={pasal_count} "
                f"anchors={parsed.source_anchor_coverage:.2%} parse={parsed.status}"
            )
            if sample_headings:
                structural = [
                    section for section in parsed.sections if section.kind != "preamble"
                ][:sample_headings]
                for section in structural:
                    print(
                        f"  page={section.page_number} kind={section.kind} "
                        f"heading={section.heading}"
                    )
            failed = failed or parsed.status != "parsed"
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify and parse manifest-listed official regulation sources"
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "manifests"
        / "personal-data-protection.v1.json",
    )
    parser.add_argument(
        "--sample-headings",
        type=int,
        default=0,
        help="Print the first N structural boundaries per document for manual review",
    )
    arguments = parser.parse_args()
    return asyncio.run(
        inspect_sources(
            arguments.manifest, sample_headings=max(arguments.sample_headings, 0)
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
