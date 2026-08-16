from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.regulasilens.ingestion import fetch_regulation
from app.regulasilens.manifest import load_manifest
from app.regulasilens.parser import (
    PARSER_VERSION,
    extract_pdf_pages,
    parse_regulation_pages,
)


async def benchmark(manifest_path: Path, evaluation_path: Path) -> int:
    manifest = load_manifest(manifest_path)
    evaluation: dict[str, Any] = json.loads(evaluation_path.read_text(encoding="utf-8"))
    cases = evaluation.get("cases", [])
    if evaluation.get("parser_version") != PARSER_VERSION or len(cases) < 30:
        raise ValueError(
            "Benchmark must target the active parser and contain at least 30 cases"
        )

    documents = {document.document_id: document for document in manifest.documents}
    observed: dict[str, set[tuple[int, str, str]]] = {}
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "NusaIntel/0.5 parser-benchmark"},
    ) as client:
        for document_id in sorted({case["document_id"] for case in cases}):
            document = documents[document_id]
            fetched = await fetch_regulation(document, client=client)
            if fetched.status != "accepted" or fetched.body is None:
                raise RuntimeError(f"Benchmark source unavailable: {document_id}")
            parsed = parse_regulation_pages(
                document_id, extract_pdf_pages(fetched.body)
            )
            observed[document_id] = {
                (section.page_number, section.kind, section.heading)
                for section in parsed.sections
            }

    failures: list[dict[str, Any]] = []
    for case in cases:
        key = (case["page_number"], case["kind"], case["heading"])
        present = key in observed[case["document_id"]]
        if present != case["expected_present"]:
            failures.append(case)
    correct = len(cases) - len(failures)
    accuracy = correct / len(cases)
    minimum = float(evaluation["minimum_accuracy"])
    print(
        json.dumps(
            {
                "benchmark_id": evaluation["benchmark_id"],
                "benchmark_version": evaluation["benchmark_version"],
                "parser_version": PARSER_VERSION,
                "correct": correct,
                "total": len(cases),
                "accuracy": accuracy,
                "minimum_accuracy": minimum,
                "passed": accuracy >= minimum,
                "failures": failures,
            },
            sort_keys=True,
        )
    )
    return 0 if accuracy >= minimum else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark legal structure boundaries")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "manifests"
        / "personal-data-protection.v1.json",
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "evaluation"
        / "parser-boundaries.v1.json",
    )
    options = parser.parse_args()
    return asyncio.run(benchmark(options.manifest, options.evaluation))


if __name__ == "__main__":
    raise SystemExit(main())
