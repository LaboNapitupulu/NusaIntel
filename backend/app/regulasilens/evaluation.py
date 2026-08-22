from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

EvaluationCategory = Literal[
    "direct_lookup",
    "paraphrased",
    "multi_section",
    "multi_document",
    "unanswerable",
    "version_sensitive",
]

REQUIRED_CATEGORIES: frozenset[EvaluationCategory] = frozenset(
    {
        "direct_lookup",
        "paraphrased",
        "multi_section",
        "multi_document",
        "unanswerable",
        "version_sensitive",
    }
)


class ExpectedReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=3)
    section_id: str = Field(min_length=8)


class EvaluationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(pattern=r"^ret-v1-[0-9]{3}$")
    text: str = Field(min_length=8)


class EvaluationTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: str = Field(pattern=r"^topic-[0-9]{2}$")
    category: EvaluationCategory
    answerable: bool
    questions: list[EvaluationQuestion] = Field(min_length=1)
    expected_relevant: list[ExpectedReference]

    @model_validator(mode="after")
    def validate_relevance(self) -> Self:
        if self.answerable != bool(self.expected_relevant):
            raise ValueError(
                "answerable topics must have references and unanswerable topics must not"
            )
        return self


class RetrievalEvaluationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    evaluation_id: str
    evaluation_version: str
    corpus_manifest_version: str
    language: Literal["id"]
    review_status: Literal["manually-reviewed"]
    reviewed_at: str
    review_method: str
    minimum_question_count: int = Field(ge=100)
    topics: list[EvaluationTopic] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_suite(self) -> Self:
        questions = [question for topic in self.topics for question in topic.questions]
        question_ids = [question.question_id for question in questions]
        topic_ids = [topic.topic_id for topic in self.topics]
        if len(questions) < self.minimum_question_count:
            raise ValueError("evaluation suite contains fewer questions than its declared minimum")
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question_id values must be unique")
        if len(topic_ids) != len(set(topic_ids)):
            raise ValueError("topic_id values must be unique")
        categories = {topic.category for topic in self.topics}
        missing = REQUIRED_CATEGORIES - categories
        if missing:
            raise ValueError(f"evaluation suite is missing categories: {sorted(missing)}")
        return self

    @property
    def question_count(self) -> int:
        return sum(len(topic.questions) for topic in self.topics)


def load_retrieval_evaluation(path: Path) -> RetrievalEvaluationSet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RetrievalEvaluationSet.model_validate(payload)
