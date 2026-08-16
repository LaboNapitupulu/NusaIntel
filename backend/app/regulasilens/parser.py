from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from pypdf import PdfReader

PARSER_VERSION = "regulation-structure-v1"
HEADING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bab", re.compile(r"^BAB\s+[IVXLCDM]+(?:\s+.*)?$", re.IGNORECASE)),
    ("bagian", re.compile(r"^Bagian\s+(?:Ke\S+|\S+)(?:\s+.*)?$", re.IGNORECASE)),
    ("paragraf", re.compile(r"^Paragraf\s+\d+(?:\s+.*)?$", re.IGNORECASE)),
    ("pasal", re.compile(r"^Pasal\s+(?:\d+[A-Z]?|[IVXLCDM]+)$", re.IGNORECASE)),
    ("ayat", re.compile(r"^\(\d+\)(?:\s+.*)?$")),
)


class DocumentParseError(ValueError):
    """Raised when a document cannot be safely parsed."""


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedSection:
    section_id: str
    order: int
    kind: Literal["preamble", "bab", "bagian", "paragraf", "pasal", "ayat"]
    heading: str
    text: str
    hierarchy: tuple[str, ...]
    page_number: int
    line_number: int
    source_anchor: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    document_id: str
    parser_version: str
    status: Literal["parsed", "needs_review"]
    sections: tuple[ParsedSection, ...]
    source_anchor_coverage: float
    reasons: tuple[str, ...]


def extract_pdf_pages(content: bytes) -> tuple[PageText, ...]:
    if not content.startswith(b"%PDF-"):
        raise DocumentParseError("Document does not have a PDF signature")
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        pages = tuple(
            PageText(page_number=index, text=page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        )
    except Exception as exc:
        raise DocumentParseError("PDF extraction failed") from exc
    if not pages or not any(page.text.strip() for page in pages):
        raise DocumentParseError("PDF contains no extractable text")
    return pages


def parse_regulation_pages(
    document_id: str,
    pages: tuple[PageText, ...],
    *,
    parser_version: str = PARSER_VERSION,
) -> ParseOutcome:
    candidates: list[tuple[str, str, list[str], int, int, tuple[str, ...]]] = []
    hierarchy: dict[str, str] = {}
    current: tuple[str, str, list[str], int, int, tuple[str, ...]] | None = None
    last_ayat_label: str | None = None

    for page in pages:
        for line_number, raw_line in enumerate(page.text.splitlines(), start=1):
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue
            match = _heading_kind(line)
            if match is not None:
                line = _normalize_heading(match, line)
                if match == "ayat":
                    ayat_label = line.split(")", 1)[0] + ")"
                    if (
                        current is not None
                        and current[0] == "ayat"
                        and ayat_label == last_ayat_label
                    ):
                        heading = current[1]
                        if ". . ." in heading and len(line) > len(heading):
                            heading = line
                        current = (
                            current[0],
                            heading,
                            [*current[2], line],
                            current[3],
                            current[4],
                            current[5],
                        )
                        continue
                    last_ayat_label = ayat_label
                elif match in {"bab", "bagian", "paragraf", "pasal"}:
                    last_ayat_label = None
                if current is not None:
                    candidates.append(current)
                _update_hierarchy(hierarchy, match, line)
                current = (
                    match,
                    line,
                    [line],
                    page.page_number,
                    line_number,
                    tuple(hierarchy.values()),
                )
            elif current is None:
                current = (
                    "preamble",
                    "Preamble",
                    [line],
                    page.page_number,
                    line_number,
                    (),
                )
            else:
                current[2].append(line)
    if current is not None:
        candidates.append(current)

    sections = tuple(
        _to_section(document_id, index, candidate)
        for index, candidate in enumerate(candidates, start=1)
    )
    reasons: list[str] = []
    if not sections:
        reasons.append("no_sections")
    if not any(section.kind == "pasal" for section in sections):
        reasons.append("no_pasal_detected")
    if len({section.section_id for section in sections}) != len(sections):
        reasons.append("duplicate_section_id")
    coverage = (
        sum(bool(section.source_anchor) for section in sections) / len(sections)
        if sections
        else 0.0
    )
    if coverage < 0.95:
        reasons.append("source_anchor_coverage_below_95_percent")
    return ParseOutcome(
        document_id=document_id,
        parser_version=parser_version,
        status="parsed" if not reasons else "needs_review",
        sections=sections,
        source_anchor_coverage=coverage,
        reasons=tuple(reasons),
    )


def _heading_kind(line: str) -> str | None:
    for kind, pattern in HEADING_PATTERNS:
        if pattern.fullmatch(line):
            return kind
    return None


def _normalize_heading(kind: str, heading: str) -> str:
    if kind == "pasal" and heading.casefold() == "pasal i":
        return "Pasal 1"
    return heading


def _update_hierarchy(hierarchy: dict[str, str], kind: str, heading: str) -> None:
    levels = ("bab", "bagian", "paragraf", "pasal", "ayat")
    index = levels.index(kind)
    for lower_level in levels[index:]:
        hierarchy.pop(lower_level, None)
    hierarchy[kind] = heading


def _to_section(
    document_id: str,
    order: int,
    candidate: tuple[str, str, list[str], int, int, tuple[str, ...]],
) -> ParsedSection:
    kind, heading, lines, page_number, line_number, hierarchy = candidate
    identity = f"{document_id}:{order}:{page_number}:{line_number}:{kind}"
    section_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
    confidence = 0.6 if kind == "preamble" else 0.95
    return ParsedSection(
        section_id=section_id,
        order=order,
        kind=kind,  # type: ignore[arg-type]
        heading=heading,
        text="\n".join(lines),
        hierarchy=hierarchy,
        page_number=page_number,
        line_number=line_number,
        source_anchor=f"page:{page_number}:line:{line_number}",
        confidence=confidence,
    )
