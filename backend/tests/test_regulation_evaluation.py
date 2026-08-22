from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.regulasilens.evaluation import REQUIRED_CATEGORIES, load_retrieval_evaluation

EVALUATION_PATH = (
    Path(__file__).parents[2] / "regulations" / "evaluation" / "retrieval-cases.v1.json"
)


def test_retrieval_evaluation_is_versioned_reviewed_and_complete() -> None:
    evaluation = load_retrieval_evaluation(EVALUATION_PATH)

    assert evaluation.evaluation_version == "1.0.0"
    assert evaluation.corpus_manifest_version == "2026-08-16.1"
    assert evaluation.review_status == "manually-reviewed"
    assert evaluation.question_count == 100
    assert {topic.category for topic in evaluation.topics} == REQUIRED_CATEGORIES
    assert any(len(topic.expected_relevant) > 1 for topic in evaluation.topics)
    assert all(
        reference.section_id for topic in evaluation.topics for reference in topic.expected_relevant
    )


def test_retrieval_evaluation_rejects_untracked_or_duplicate_cases(tmp_path: Path) -> None:
    payload = EVALUATION_PATH.read_text(encoding="utf-8")
    payload = payload.replace('"ret-v1-002"', '"ret-v1-001"', 1)
    invalid = tmp_path / "invalid.json"
    invalid.write_text(payload, encoding="utf-8")

    with pytest.raises(ValidationError, match="question_id values must be unique"):
        load_retrieval_evaluation(invalid)
