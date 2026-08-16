from __future__ import annotations

import json
from pathlib import Path

from app.regulasilens.parser import PageText, parse_regulation_pages

EVALUATION_PATH = (
    Path(__file__).parents[2] / "regulations" / "evaluation" / "parser-boundaries.v1.json"
)


def test_structure_parser_preserves_order_hierarchy_and_anchors() -> None:
    pages = (
        PageText(
            page_number=1,
            text="""UNDANG-UNDANG REPUBLIK INDONESIA
BAB I
KETENTUAN UMUM
Pasal 1
Dalam Undang-Undang ini yang dimaksud dengan Data Pribadi adalah data tentang orang.
(1) Pemrosesan dilakukan secara terbatas.
(2) Pemrosesan dilakukan secara sah.""",
        ),
        PageText(
            page_number=2,
            text="""BAB II
HAK SUBJEK DATA PRIBADI
Bagian Kesatu
Pasal 5
Subjek Data Pribadi berhak mendapatkan informasi.""",
        ),
    )

    outcome = parse_regulation_pages("uu-27-2022", pages)

    assert outcome.status == "parsed"
    assert outcome.source_anchor_coverage == 1.0
    assert [section.order for section in outcome.sections] == list(
        range(1, len(outcome.sections) + 1)
    )
    assert len({section.section_id for section in outcome.sections}) == len(outcome.sections)
    assert all(section.source_anchor.startswith("page:") for section in outcome.sections)
    pasal_five = next(section for section in outcome.sections if section.heading == "Pasal 5")
    assert pasal_five.page_number == 2
    assert pasal_five.hierarchy[-1] == "Pasal 5"


def test_parser_marks_unstructured_text_for_review() -> None:
    outcome = parse_regulation_pages(
        "unknown-document",
        (PageText(page_number=1, text="Dokumen tanpa struktur pasal yang dapat dikenali."),),
    )

    assert outcome.status == "needs_review"
    assert "no_pasal_detected" in outcome.reasons


def test_parser_normalizes_ocr_pasal_one_and_page_boundary_ayat() -> None:
    outcome = parse_regulation_pages(
        "uu-27-2022",
        (
            PageText(page_number=1, text="BAB I\nPasal I\n(1) Ketentuan . . ."),
            PageText(page_number=2, text="(1) Ketentuan lengkap\nlanjutan"),
        ),
    )

    headings = [section.heading for section in outcome.sections]
    assert "Pasal 1" in headings
    assert headings.count("(1) Ketentuan lengkap") == 1


def test_parser_benchmark_is_versioned_and_has_reviewed_coverage() -> None:
    benchmark = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))

    assert benchmark["parser_version"] == "regulation-structure-v1"
    assert benchmark["minimum_accuracy"] >= 0.95
    assert len(benchmark["cases"]) >= 30
    assert {case["document_id"] for case in benchmark["cases"]} == {
        "uu-27-2022",
        "pp-71-2019",
        "permenkominfo-20-2016",
    }
    assert any(not case["expected_present"] for case in benchmark["cases"])
