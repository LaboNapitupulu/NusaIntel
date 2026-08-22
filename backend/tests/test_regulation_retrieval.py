from __future__ import annotations

from app.regulasilens.retrieval import RetrievalIndex, SourceSection


def section(
    section_id: str,
    heading: str,
    text: str,
    *,
    document_id: str = "uu-27-2022",
    order: int = 1,
) -> SourceSection:
    return SourceSection(
        section_id=section_id,
        document_id=document_id,
        document_version_id=f"version-{document_id}",
        manifest_version="2026-08-16.1",
        document_title="Pelindungan Data Pribadi",
        document_status="in_force",
        heading=heading,
        text=text,
        source_url=f"https://peraturan.bpk.go.id/{document_id}",
        source_anchor=f"page:1:line:{order}",
        section_order=order,
    )


SECTIONS = (
    section(
        "access",
        "Pasal 7",
        "Subjek Data Pribadi berhak mendapatkan akses dan memperoleh salinan Data Pribadi.",
    ),
    section(
        "erase",
        "Pasal 8",
        (
            "Subjek Data Pribadi berhak mengakhiri pemrosesan, menghapus, "
            "dan memusnahkan Data Pribadi."
        ),
        order=2,
    ),
    section(
        "secure",
        "Pasal 35",
        "Pengendali wajib melindungi dan memastikan keamanan Data Pribadi dengan langkah teknis.",
        order=3,
    ),
    section(
        "software",
        "Pasal 8",
        "Perangkat Lunak harus terjamin keamanan dan keandalan operasi.",
        document_id="pp-71-2019",
    ),
)


def test_bm25_dense_and_hybrid_retrieve_expected_sections() -> None:
    index = RetrievalIndex(SECTIONS, chunker="structure")

    bm25 = index.search("hak memperoleh salinan data", method="bm25")
    dense = index.search("cara melihat data personal saya", method="dense")
    hybrid = index.search("kewajiban pengamanan informasi pribadi", method="hybrid_rerank")

    assert bm25.hits[0].section_ids == ("access",)
    assert dense.hits[0].section_ids == ("access",)
    assert hybrid.hits[0].section_ids == ("secure",)
    assert hybrid.hits[0].source_anchor.startswith("page:")
    assert hybrid.hits[0].source_url.startswith("https://")
    assert hybrid.index_version
    assert hybrid.corpus_version == "2026-08-16.1"


def test_fixed_chunks_preserve_all_member_section_ids_and_provenance() -> None:
    index = RetrievalIndex(SECTIONS, chunker="fixed")
    outcome = index.search("hapus data", method="hybrid")

    assert "erase" in outcome.hits[0].section_ids
    assert outcome.chunker_version == "fixed-1600-char-v1"
    assert ".." in outcome.hits[0].source_anchor


def test_retrieval_is_deterministic_and_validates_inputs() -> None:
    first = RetrievalIndex(SECTIONS, chunker="structure")
    second = RetrievalIndex(SECTIONS, chunker="structure")

    assert first.index_version == second.index_version
    assert first.search("keamanan", method="hybrid") == second.search("keamanan", method="hybrid")
