from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.regulasilens.retrieval import SearchHit

ANSWER_PIPELINE_VERSION = "evidence-extractive-id-v1"
CITATION_PATTERN = re.compile(r"\[(C[1-9][0-9]*)\]")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?;])\s+|\n+")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

STOPWORDS = frozenset(
    {
        "apa",
        "apakah",
        "atau",
        "bagaimana",
        "dalam",
        "dan",
        "dari",
        "dengan",
        "di",
        "ini",
        "itu",
        "mana",
        "menurut",
        "oleh",
        "pada",
        "saya",
        "serta",
        "yang",
        "untuk",
    }
)
OUT_OF_DOMAIN_TERMS = frozenset(
    {
        "akreditasi",
        "cuti",
        "dividen",
        "dokter",
        "film",
        "gawat",
        "hak cipta",
        "lembur",
        "merek",
        "obat",
        "pajak",
        "pembajakan",
        "pegawai",
        "pekerja",
        "pesangon",
        "puskesmas",
        "rumah sakit",
        "spt",
        "tempat tidur",
        "upah",
    }
)
IN_DOMAIN_TERMS = frozenset(
    {
        "akses",
        "data",
        "informasi elektronik",
        "keamanan",
        "kebocoran",
        "pelindungan",
        "pemrosesan",
        "pengendali",
        "permenkominfo",
        "persetujuan",
        "pribadi",
        "prosesor",
        "sistem elektronik",
        "subjek",
        "transfer",
        "uu 27",
    }
)

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True, slots=True)
class AnswerEvidence:
    hit: SearchHit
    text: str


@dataclass(frozen=True, slots=True)
class Citation:
    citation_id: str
    section_ids: tuple[str, ...]
    document_id: str
    document_version_id: str
    document_title: str
    document_status: str
    heading: str
    quote: str
    source_url: str
    source_anchor: str
    status_checked_at: str | None

    def serialize(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "section_ids": list(self.section_ids),
            "document_id": self.document_id,
            "document_version_id": self.document_version_id,
            "document_title": self.document_title,
            "document_status": self.document_status,
            "heading": self.heading,
            "quote": self.quote,
            "source_url": self.source_url,
            "source_anchor": self.source_anchor,
            "status_checked_at": self.status_checked_at,
        }


def generate_grounded_answer(
    question: str,
    evidence: tuple[AnswerEvidence, ...],
    *,
    maximum_citations: int = 5,
) -> dict[str, Any]:
    normalized_question = " ".join(question.split())
    if _outside_supported_domain(normalized_question):
        return _refusal(
            normalized_question,
            "Pertanyaan berada di luar corpus pelindungan data pribadi yang tersedia.",
        )

    selected: list[tuple[AnswerEvidence, str, float]] = []
    seen_quotes: set[str] = set()
    for item in evidence:
        quote, overlap = _best_supported_sentence(normalized_question, item.text)
        if not quote or quote.casefold() in seen_quotes:
            continue
        seen_quotes.add(quote.casefold())
        selected.append((item, quote, overlap))
    selected.sort(
        key=lambda item: (
            -(_intent_bonus(normalized_question, item[1]) + item[2]),
            -item[0].hit.score,
            item[0].hit.rank,
        )
    )
    selected = selected[:maximum_citations]

    coverage = _evidence_coverage(normalized_question, tuple(quote for _, quote, _ in selected))
    if not selected or coverage < 0.16:
        return _refusal(
            normalized_question,
            "Evidence yang ditemukan belum cukup untuk menjawab tanpa membuat klaim tambahan.",
        )

    citations = tuple(
        Citation(
            citation_id=f"C{index}",
            section_ids=item.hit.section_ids,
            document_id=item.hit.document_id,
            document_version_id=item.hit.document_version_id,
            document_title=item.hit.document_title,
            document_status=item.hit.document_status,
            heading=item.hit.heading,
            quote=quote,
            source_url=item.hit.source_url,
            source_anchor=item.hit.source_anchor,
            status_checked_at=item.hit.status_checked_at,
        )
        for index, (item, quote, _) in enumerate(selected, start=1)
    )
    claims = tuple(f"{citation.quote} [{citation.citation_id}]" for citation in citations)
    answer = "\n".join(f"- {claim}" for claim in claims)
    validation = validate_citations(answer, citations)
    if not validation["valid"]:
        return _refusal(
            normalized_question,
            "Validasi citation gagal; jawaban ditahan agar tidak menampilkan klaim tanpa sumber.",
        )

    confidence: Confidence = "high" if coverage >= 0.65 else "medium" if coverage >= 0.35 else "low"
    return {
        "question": normalized_question,
        "answerable": True,
        "answer": answer,
        "confidence": confidence,
        "evidence_coverage": round(coverage, 4),
        "refusal_reason": None,
        "citations": [citation.serialize() for citation in citations],
        "citation_validation": validation,
        "disclaimer": (
            "Ringkasan ini hanya menampilkan teks dari corpus regulasi yang tersedia dan bukan "
            "nasihat hukum. Periksa dokumen resmi serta status terbarunya sebelum mengambil "
            "keputusan."
        ),
        "pipeline_version": ANSWER_PIPELINE_VERSION,
    }


def validate_citations(answer: str, citations: tuple[Citation, ...]) -> dict[str, Any]:
    available = {citation.citation_id for citation in citations}
    markers = CITATION_PATTERN.findall(answer)
    marker_set = set(markers)
    claims = [line.strip() for line in answer.splitlines() if line.strip()]
    unsupported_claims = [claim for claim in claims if not CITATION_PATTERN.search(claim)]
    fabricated = sorted(marker_set - available)
    unused = sorted(available - marker_set)
    return {
        "valid": not fabricated and not unsupported_claims,
        "markers": markers,
        "fabricated_markers": fabricated,
        "unused_citations": unused,
        "material_claim_count": len(claims),
        "cited_claim_count": len(claims) - len(unsupported_claims),
        "coverage": ((len(claims) - len(unsupported_claims)) / len(claims) if claims else 1.0),
    }


def _refusal(question: str, reason: str) -> dict[str, Any]:
    return {
        "question": question,
        "answerable": False,
        "answer": (
            "Saya belum dapat menjawab berdasarkan corpus yang tersedia. "
            "Coba persempit pertanyaan ke regulasi pelindungan data pribadi."
        ),
        "confidence": "low",
        "evidence_coverage": 0.0,
        "refusal_reason": reason,
        "citations": [],
        "citation_validation": {
            "valid": True,
            "markers": [],
            "fabricated_markers": [],
            "unused_citations": [],
            "material_claim_count": 0,
            "cited_claim_count": 0,
            "coverage": 1.0,
        },
        "disclaimer": (
            "Corpus beta hanya mencakup domain pelindungan data pribadi dan tidak menggantikan "
            "nasihat hukum."
        ),
        "pipeline_version": ANSWER_PIPELINE_VERSION,
    }


def _outside_supported_domain(question: str) -> bool:
    normalized = question.casefold()
    outside = any(term in normalized for term in OUT_OF_DOMAIN_TERMS)
    inside = any(term in normalized for term in IN_DOMAIN_TERMS)
    return outside and not inside


def _terms(text: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 1 and token.casefold() not in STOPWORDS
    }


def _best_supported_sentence(question: str, text: str) -> tuple[str, float]:
    query_terms = _terms(question)
    candidates = [" ".join(item.split()) for item in SENTENCE_PATTERN.split(text) if item.strip()]
    if not candidates:
        return "", 0.0
    scored = [
        (len(query_terms & _terms(candidate)) / max(1, len(query_terms)), -index, candidate)
        for index, candidate in enumerate(candidates)
    ]
    overlap, _, quote = max(scored)
    if len(quote) > 700:
        quote = f"{quote[:697].rstrip()}..."
    return quote, overlap


def _evidence_coverage(question: str, quotes: tuple[str, ...]) -> float:
    query_terms = _terms(question)
    if not query_terms:
        return 0.0
    evidence_terms = _terms(" ".join(quotes))
    return len(query_terms & evidence_terms) / len(query_terms)


def _intent_bonus(question: str, quote: str) -> float:
    normalized_question = question.casefold()
    normalized_quote = quote.casefold()
    asks_effective_date = any(
        phrase in normalized_question
        for phrase in ("berlaku", "diundangkan", "efektif", "ketentuan penutup")
    )
    states_effective_date = any(
        phrase in normalized_quote
        for phrase in ("mulai berlaku", "tanggal diundangkan", "ketentuan penutup")
    )
    return 1.0 if asks_effective_date and states_effective_date else 0.0
