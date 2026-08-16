from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.regulasilens.manifest import ManifestError, load_manifest

MANIFEST_PATH = (
    Path(__file__).parents[2] / "regulations" / "manifests" / "personal-data-protection.v1.json"
)


def test_initial_manifest_is_strict_and_checksum_complete() -> None:
    manifest = load_manifest(MANIFEST_PATH)

    assert manifest.domain == "personal-data-protection"
    assert len(manifest.documents) == 3
    assert len({document.document_id for document in manifest.documents}) == 3
    assert all(len(document.expected_sha256) == 64 for document in manifest.documents)
    assert all(document.status == "in_force" for document in manifest.documents)
    assert manifest.source_policy.redistribution == "link-and-local-cache-only"


def test_manifest_rejects_unapproved_download_host(tmp_path: Path) -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["documents"][0]["content_url"] = "https://example.com/unofficial.pdf"
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(invalid_path)


def test_manifest_keeps_external_relation_explicit() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    pp = next(document for document in manifest.documents if document.document_id == "pp-71-2019")

    assert pp.relations[0].relation_type == "revokes"
    assert pp.relations[0].target_document_id is None
    assert "PP Nomor 82 Tahun 2012" in pp.relations[0].target_citation
