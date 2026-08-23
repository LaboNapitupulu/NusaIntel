from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.regulasilens.evaluation import load_retrieval_evaluation
from app.regulasilens.service import CorpusService


def percentile_95(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]


async def evaluate(
    evaluation_path: Path,
    configuration_path: Path,
    output_path: Path | None,
) -> int:
    suite = load_retrieval_evaluation(evaluation_path)
    configuration = json.loads(configuration_path.read_text(encoding="utf-8"))
    targets = configuration["targets"]
    engine = create_database_engine(get_settings().resolved_database_url)
    service = CorpusService(create_session_factory(engine), answer_timeout_seconds=9.0)
    latencies: list[float] = []
    retrieval_recalls: list[float] = []
    claim_coverages: list[float] = []
    citation_total = 0
    correct_citations = 0
    marker_total = 0
    fabricated_markers = 0
    unanswerable_total = 0
    correct_refusals = 0
    answerable_total = 0
    supported_answers = 0
    version_total = 0
    correct_versions = 0
    openable_total = 0
    openable_citations = 0
    failures: list[dict[str, Any]] = []

    try:
        for topic in suite.topics:
            expected = {reference.section_id for reference in topic.expected_relevant}
            for question in topic.questions:
                started = time.perf_counter()
                answer = await service.answer(question.text)
                latencies.append(time.perf_counter() - started)
                search = await service.search(question.text, limit=10)
                retrieved = {
                    section_id
                    for hit in search["hits"]
                    for section_id in hit["section_ids"]
                }
                if topic.answerable:
                    retrieval_recalls.append(len(expected & retrieved) / len(expected))
                    answerable_total += 1
                    if not answer["answerable"]:
                        claim_coverages.append(0.0)
                else:
                    unanswerable_total += 1
                    if not answer["answerable"] and not answer["citations"]:
                        correct_refusals += 1

                citations = answer["citations"]
                cited_sections = {
                    section_id
                    for citation in citations
                    for section_id in citation["section_ids"]
                }
                if topic.answerable and expected & cited_sections:
                    supported_answers += 1
                if topic.category == "version_sensitive":
                    version_total += 1
                    if answer["answerable"] and expected & cited_sections:
                        correct_versions += 1

                validation = answer["citation_validation"]
                if answer["answerable"]:
                    claim_coverages.append(float(validation["coverage"]))
                marker_total += len(validation["markers"])
                fabricated_markers += len(validation["fabricated_markers"])
                citation_total += len(citations)
                correct_citations += sum(
                    1
                    for citation in citations
                    if citation["citation_id"] in validation["markers"]
                    and citation["quote"]
                    and citation["source_url"].startswith("https://")
                    and citation["source_anchor"].startswith("page:")
                )
                for citation in citations:
                    openable_total += 1
                    context = None
                    for section_id in citation["section_ids"]:
                        context = await service.section_context(
                            citation["document_id"],
                            section_id,
                            version_id=citation["document_version_id"],
                            before=0,
                            after=0,
                        )
                        if context is not None:
                            break
                    if context is not None:
                        openable_citations += 1

                if topic.answerable and (
                    not answer["answerable"] or not expected & cited_sections
                ):
                    expected_ranks = [
                        hit["rank"]
                        for hit in search["hits"]
                        if expected & set(hit["section_ids"])
                    ]
                    expected_hits = [
                        {
                            "rank": hit["rank"],
                            "heading": hit["heading"],
                            "excerpt": hit["excerpt"],
                        }
                        for hit in search["hits"]
                        if expected & set(hit["section_ids"])
                    ]
                    failures.append(
                        {
                            "question_id": question.question_id,
                            "category": topic.category,
                            "reason": "refused_or_expected_section_not_cited",
                            "expected_section_ids": sorted(expected),
                            "cited_section_ids": sorted(cited_sections),
                            "retrieved_expected_ranks": expected_ranks,
                            "retrieved_expected_hits": expected_hits,
                        }
                    )
    finally:
        await engine.dispose()

    metrics = {
        "retrieval_recall_at_10": sum(retrieval_recalls) / len(retrieval_recalls),
        "citation_correctness": correct_citations / citation_total
        if citation_total
        else 1.0,
        "citation_coverage": sum(claim_coverages) / len(claim_coverages),
        "refusal_accuracy": correct_refusals / unanswerable_total,
        "fabricated_citation_rate": fabricated_markers / marker_total
        if marker_total
        else 0.0,
        "version_sensitive_accuracy": correct_versions / version_total,
        "answer_supported_by_expected_section": supported_answers / answerable_total,
        "openable_citation_rate": openable_citations / openable_total
        if openable_total
        else 1.0,
        "end_to_end_p95_seconds": percentile_95(latencies),
    }
    passed = (
        metrics["retrieval_recall_at_10"] >= targets["retrieval_recall_at_10_minimum"]
        and metrics["citation_correctness"] >= targets["citation_correctness_minimum"]
        and metrics["citation_coverage"] >= targets["citation_coverage_minimum"]
        and metrics["refusal_accuracy"] >= targets["refusal_accuracy_minimum"]
        and metrics["fabricated_citation_rate"]
        <= targets["fabricated_citation_rate_maximum"]
        and metrics["version_sensitive_accuracy"]
        >= targets["version_sensitive_accuracy_minimum"]
        and metrics["end_to_end_p95_seconds"]
        < targets["end_to_end_p95_seconds_maximum"]
        and metrics["openable_citation_rate"] == 1.0
    )
    report = {
        "evaluation_id": configuration["evaluation_id"],
        "evaluation_version": configuration["evaluation_version"],
        "pipeline_version": configuration["pipeline_version"],
        "question_count": suite.question_count,
        "targets": targets,
        "metrics": metrics,
        "passed": passed,
        "failure_count": len(failures),
        "failures": failures,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{encoded}\n", encoding="utf-8")
    print(encoded)
    return 0 if passed else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark RegulasiLens grounded answers"
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "evaluation"
        / "retrieval-cases.v1.json",
    )
    parser.add_argument(
        "--configuration",
        type=Path,
        default=REPOSITORY_ROOT
        / "regulations"
        / "evaluation"
        / "answer-evaluation.v1.json",
    )
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    return asyncio.run(
        evaluate(options.evaluation, options.configuration, options.output)
    )


if __name__ == "__main__":
    raise SystemExit(main())
