from __future__ import annotations

from app.regulasilens.comparison import VersionSection, compare_version_sections


def section(identifier: str, heading: str, text: str, order: int) -> VersionSection:
    return VersionSection(
        section_id=identifier,
        section_order=order,
        kind="pasal",
        heading=heading,
        hierarchy=("BAB I",),
        text=text,
        source_anchor=f"page:1:line:{order}",
    )


def test_structured_comparison_shows_source_text_for_every_change() -> None:
    base = (
        section("a1", "Pasal 1", "Data wajib dilindungi.", 1),
        section("a2", "Pasal 2", "Ketentuan lama.", 2),
    )
    target = (
        section("b1", "Pasal 1", "Data wajib dilindungi dengan langkah teknis.", 1),
        section("b3", "Pasal 3", "Ketentuan baru.", 3),
    )

    result = compare_version_sections(base, target)

    assert result["counts"] == {"added": 1, "removed": 1, "modified": 1}
    for change in result["changes"]:
        assert change["base"] is not None or change["target"] is not None
        assert (change["base"] or change["target"])["text"]
    modified = next(item for item in result["changes"] if item["change_type"] == "modified")
    assert modified["base"]["text"] == "Data wajib dilindungi."
    assert modified["target"]["text"].endswith("teknis.")
