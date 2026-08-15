from __future__ import annotations

from app.regulasilens.parser import PageText, parse_regulation_pages


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
