from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal

ChangeType = Literal["added", "removed", "modified"]
COMPARISON_VERSION = "structured-section-diff-v1"


@dataclass(frozen=True, slots=True)
class VersionSection:
    section_id: str
    section_order: int
    kind: str
    heading: str
    hierarchy: tuple[str, ...]
    text: str
    source_anchor: str


def compare_version_sections(
    base: tuple[VersionSection, ...], target: tuple[VersionSection, ...]
) -> dict[str, Any]:
    base_map = {_identity(section): section for section in base}
    target_map = {_identity(section): section for section in target}
    changes: list[dict[str, Any]] = []

    for identity in sorted(set(base_map) | set(target_map)):
        left = base_map.get(identity)
        right = target_map.get(identity)
        if left is None and right is not None:
            changes.append(_change("added", None, right))
        elif right is None and left is not None:
            changes.append(_change("removed", left, None))
        elif (
            left is not None
            and right is not None
            and _normalize(left.text) != _normalize(right.text)
        ):
            changes.append(_change("modified", left, right))

    counts = {
        change_type: sum(1 for change in changes if change["change_type"] == change_type)
        for change_type in ("added", "removed", "modified")
    }
    return {
        "comparison_version": COMPARISON_VERSION,
        "counts": counts,
        "unchanged_count": len(set(base_map) & set(target_map)) - counts["modified"],
        "changes": changes,
    }


def _identity(section: VersionSection) -> str:
    hierarchy = "/".join(_normalize(value) for value in section.hierarchy)
    return f"{section.kind.casefold()}|{hierarchy}|{_normalize(section.heading)}"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _change(
    change_type: ChangeType,
    base: VersionSection | None,
    target: VersionSection | None,
) -> dict[str, Any]:
    left_text = base.text if base is not None else None
    right_text = target.text if target is not None else None
    similarity = (
        round(SequenceMatcher(None, _normalize(left_text), _normalize(right_text)).ratio(), 4)
        if left_text is not None and right_text is not None
        else None
    )
    reference = target or base
    assert reference is not None
    return {
        "change_type": change_type,
        "heading": reference.heading,
        "kind": reference.kind,
        "base": _source(base),
        "target": _source(target),
        "text_similarity": similarity,
        "summary": {
            "added": "Bagian ditambahkan pada versi target.",
            "removed": "Bagian tidak ditemukan pada versi target.",
            "modified": "Teks bagian berubah; kedua teks sumber ditampilkan.",
        }[change_type],
    }


def _source(section: VersionSection | None) -> dict[str, Any] | None:
    if section is None:
        return None
    return {
        "section_id": section.section_id,
        "section_order": section.section_order,
        "heading": section.heading,
        "text": section.text,
        "source_anchor": section.source_anchor,
    }
