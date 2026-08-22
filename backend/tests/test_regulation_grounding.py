from __future__ import annotations

from app.regulasilens.grounding import (
    AnswerEvidence,
    Citation,
    generate_grounded_answer,
    validate_citations,
)
from app.regulasilens.retrieval import SearchHit


def hit(*, section_id: str = "section-access") -> SearchHit:
    return SearchHit(
        rank=1,
        chunk_id="chunk-1",
        section_ids=(section_id,),
        document_id="uu-27-2022",
        document_version_id="version-1",
        document_title="Pelindungan Data Pribadi",
        document_status="in_force",
        heading="Pasal 7",
        excerpt="Subjek Data Pribadi berhak memperoleh akses.",
        source_url="https://peraturan.bpk.go.id/uu-27-2022",
        source_anchor="page:4:line:10",
        score=0.9,
        bm25_score=1.0,
        dense_score=0.8,
        status_checked_at="2026-08-16",
    )


def test_grounded_answer_uses_only_evidence_and_valid_citations() -> None:
    text = (
        "Subjek Data Pribadi berhak mendapatkan akses dan memperoleh salinan Data Pribadi. "
        "Akses diberikan sesuai ketentuan peraturan perundang-undangan."
    )
    result = generate_grounded_answer(
        "Apa hak akses dan salinan Data Pribadi?",
        (AnswerEvidence(hit=hit(), text=text),),
    )

    assert result["answerable"] is True
    assert "[C1]" in result["answer"]
    assert result["citations"][0]["quote"] in text
    assert result["citation_validation"]["valid"] is True
    assert result["citation_validation"]["coverage"] == 1.0


def test_grounded_answer_refuses_out_of_domain_question() -> None:
    result = generate_grounded_answer(
        "Berapa upah minimum provinsi DKI Jakarta tahun 2026?",
        (AnswerEvidence(hit=hit(), text="Data Pribadi wajib dilindungi."),),
    )

    assert result["answerable"] is False
    assert result["citations"] == []
    assert "di luar corpus" in result["refusal_reason"]


def test_citation_validator_rejects_fabricated_marker() -> None:
    citation = Citation(
        citation_id="C1",
        section_ids=("section-access",),
        document_id="uu-27-2022",
        document_version_id="version-1",
        document_title="Pelindungan Data Pribadi",
        document_status="in_force",
        heading="Pasal 7",
        quote="Hak akses tersedia.",
        source_url="https://peraturan.bpk.go.id/uu-27-2022",
        source_anchor="page:4:line:10",
        status_checked_at="2026-08-16",
    )

    result = validate_citations("Hak akses tersedia. [C99]", (citation,))

    assert result["valid"] is False
    assert result["fabricated_markers"] == ["C99"]
