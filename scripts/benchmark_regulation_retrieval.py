from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.regulasilens.evaluation import EvaluationTopic, load_retrieval_evaluation
from app.regulasilens.retrieval import Chunker, SearchMethod
from app.regulasilens.service import CorpusService

TARGET_RECALL_AT_10 = 0.85
TARGET_P95_SECONDS = 1.5


def percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def retrieved_sections(hits: list[dict[str, Any]], limit: int) -> set[str]:
    return {
        str(section_id)
        for hit in hits[:limit]
        for section_id in hit.get("section_ids", [])
    }


async def evaluate_configuration(
    service: CorpusService,
    topics: list[EvaluationTopic],
    *,
    method: SearchMethod,
    chunker: Chunker,
) -> dict[str, Any]:
    latencies: list[float] = []
    recall_at_5: list[float] = []
    recall_at_10: list[float] = []
    failures: list[dict[str, Any]] = []
    category_recall: dict[str, list[float]] = defaultdict(list)
    anchor_hits = 0
    total_hits = 0
    provenance: dict[str, Any] | None = None

    for topic in topics:
        expected = {reference.section_id for reference in topic.expected_relevant}
        for question in topic.questions:
            started = perf_counter()
            outcome = await service.search(
                question.text,
                method=method,
                chunker=chunker,
                limit=10,
            )
            latencies.append(perf_counter() - started)
            hits = outcome["hits"]
            provenance = outcome["provenance"]
            total_hits += len(hits)
            anchor_hits += sum(
                bool(hit.get("source_anchor") and hit.get("source_url")) for hit in hits
            )
            if not topic.answerable:
                continue
            found_at_5 = retrieved_sections(hits, 5)
            found_at_10 = retrieved_sections(hits, 10)
            question_recall_5 = len(expected & found_at_5) / len(expected)
            question_recall_10 = len(expected & found_at_10) / len(expected)
            recall_at_5.append(question_recall_5)
            recall_at_10.append(question_recall_10)
            category_recall[topic.category].append(question_recall_10)
            if question_recall_10 < 1:
                failures.append(
                    {
                        "question_id": question.question_id,
                        "topic_id": topic.topic_id,
                        "category": topic.category,
                        "expected_section_ids": sorted(expected),
                        "retrieved_section_ids": sorted(found_at_10),
                        "recall_at_10": question_recall_10,
                    }
                )

    return {
        "method": method,
        "chunker": chunker,
        "question_count": sum(len(topic.questions) for topic in topics),
        "answerable_question_count": len(recall_at_10),
        "recall_at_5": sum(recall_at_5) / len(recall_at_5),
        "recall_at_10": sum(recall_at_10) / len(recall_at_10),
        "latency_p95_seconds": percentile_95(latencies),
        "source_anchor_coverage": anchor_hits / total_hits if total_hits else 0.0,
        "category_recall_at_10": {
            category: sum(values) / len(values)
            for category, values in sorted(category_recall.items())
        },
        "failure_count": len(failures),
        "failures": failures,
        "provenance": provenance,
    }


async def benchmark(evaluation_path: Path, output_path: Path | None) -> int:
    evaluation = load_retrieval_evaluation(evaluation_path)
    engine = create_database_engine(get_settings().resolved_database_url)
    service = CorpusService(create_session_factory(engine))
    try:
        configurations: tuple[tuple[SearchMethod, Chunker], ...] = (
            ("bm25", "structure"),
            ("dense", "structure"),
            ("hybrid", "structure"),
            ("hybrid_rerank", "structure"),
            ("hybrid", "fixed"),
            ("hybrid_rerank", "fixed"),
        )
        results = [
            await evaluate_configuration(
                service,
                evaluation.topics,
                method=method,
                chunker=chunker,
            )
            for method, chunker in configurations
        ]
    finally:
        await engine.dispose()

    primary = next(
        result
        for result in results
        if result["method"] == "hybrid_rerank" and result["chunker"] == "fixed"
    )
    passed = (
        primary["recall_at_10"] >= TARGET_RECALL_AT_10
        and primary["latency_p95_seconds"] < TARGET_P95_SECONDS
        and primary["source_anchor_coverage"] == 1.0
    )
    report = {
        "benchmark_id": evaluation.evaluation_id,
        "evaluation_version": evaluation.evaluation_version,
        "corpus_manifest_version": evaluation.corpus_manifest_version,
        "question_count": evaluation.question_count,
        "targets": {
            "hybrid_rerank_selected_recall_at_10_minimum": TARGET_RECALL_AT_10,
            "hybrid_rerank_selected_latency_p95_seconds_maximum": TARGET_P95_SECONDS,
            "source_anchor_coverage": 1.0,
        },
        "passed": passed,
        "results": results,
        "reranker_decision": (
            "adopted" if primary["recall_at_10"] >= TARGET_RECALL_AT_10 else "iterate"
        ),
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{encoded}\n", encoding="utf-8")
    print(encoded)
    return 0 if passed else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark RegulasiLens retrieval baselines")
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=REPOSITORY_ROOT / "regulations" / "evaluation" / "retrieval-cases.v1.json",
    )
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    return asyncio.run(benchmark(options.evaluation, options.output))


if __name__ == "__main__":
    raise SystemExit(main())
