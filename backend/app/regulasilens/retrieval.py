from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Literal

RETRIEVAL_VERSION = "regulation-retrieval-v1"
BM25_VERSION = "bm25-k1-1.5-b-0.75-v1"
DENSE_VERSION = "hashing-tfidf-2048-id-v1"
HYBRID_VERSION = "rrf-k60-v1"
RERANKER_VERSION = "legal-coverage-diversity-v1"
STRUCTURE_CHUNKER_VERSION = "legal-structure-v1"
FIXED_CHUNKER_VERSION = "fixed-1600-char-v1"

SearchMethod = Literal["bm25", "dense", "hybrid", "hybrid_rerank"]
Chunker = Literal["structure", "fixed"]

TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("akses", "salinan", "melihat", "mengakses"),
    (
        "aman",
        "keamanan",
        "pengamanan",
        "melindungi",
        "perlindungan",
        "keandalan",
        "kerahasiaan",
        "keutuhan",
        "ketersediaan",
    ),
    ("benar", "koreksi", "pembetulan", "memperbaiki", "pembaruan", "memperbarui"),
    ("denda", "ganti", "kompensasi", "kerugian", "rugi"),
    ("definisi", "pengertian", "dimaksud"),
    ("efektif", "berlaku", "keberlakuan", "diundangkan"),
    ("hapus", "menghapus", "penghapusan", "memusnahkan", "pemusnahan"),
    ("hak", "berhak"),
    ("izin", "persetujuan", "consent"),
    ("insiden", "kebocoran", "kegagalan", "pelanggaran"),
    ("jenis", "klasifikasi", "pengelompokan", "terdiri"),
    ("luar", "internasional", "lintas"),
    ("notifikasi", "pemberitahuan", "mengabarkan"),
    ("petugas", "pejabat", "dpo"),
    ("pindah", "transfer", "pemindahan"),
    ("pribadi", "personal", "perseorangan"),
    ("tenggat", "batas", "lambat"),
    ("tarik", "menarik", "mencabut", "pencabutan"),
    ("tidaksah", "ilegal", "melawan", "melanggar"),
    ("wajib", "kewajiban", "harus", "perlu"),
)
SYNONYM_LOOKUP = {term: group[0] for group in SYNONYM_GROUPS for term in group}
STOPWORDS = frozenset(
    {
        "apa",
        "apakah",
        "atas",
        "atau",
        "bagaimana",
        "bagian",
        "bagi",
        "dalam",
        "dan",
        "dari",
        "dengan",
        "di",
        "dimana",
        "ini",
        "itu",
        "kepada",
        "kembali",
        "mana",
        "menurut",
        "oleh",
        "pada",
        "saya",
        "saja",
        "sebuah",
        "serta",
        "yang",
        "untuk",
    }
)


@dataclass(frozen=True, slots=True)
class SourceSection:
    section_id: str
    document_id: str
    document_version_id: str
    manifest_version: str
    document_title: str
    document_status: str
    heading: str
    text: str
    source_url: str
    source_anchor: str
    section_order: int
    status_checked_at: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalChunk:
    chunk_id: str
    section_ids: tuple[str, ...]
    document_id: str
    document_version_id: str
    manifest_version: str
    document_title: str
    document_status: str
    heading: str
    text: str
    source_url: str
    source_anchor: str
    is_explanation: bool = False
    status_checked_at: str | None = None

    @property
    def searchable_text(self) -> str:
        return " ".join((self.heading, self.text))


@dataclass(frozen=True, slots=True)
class SearchHit:
    rank: int
    chunk_id: str
    section_ids: tuple[str, ...]
    document_id: str
    document_version_id: str
    document_title: str
    document_status: str
    heading: str
    excerpt: str
    source_url: str
    source_anchor: str
    score: float
    bm25_score: float | None
    dense_score: float | None
    status_checked_at: str | None = None


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    query: str
    method: SearchMethod
    hits: tuple[SearchHit, ...]
    corpus_version: str
    index_version: str
    retrieval_version: str
    bm25_version: str
    dense_version: str
    hybrid_version: str
    reranker_version: str
    chunker_version: str


class RetrievalIndex:
    def __init__(self, sections: tuple[SourceSection, ...], *, chunker: Chunker) -> None:
        if not sections:
            raise ValueError("Cannot build a retrieval index without published sections")
        self.chunker = chunker
        self.chunker_version = (
            STRUCTURE_CHUNKER_VERSION if chunker == "structure" else FIXED_CHUNKER_VERSION
        )
        self.chunks = (
            _structure_chunks(sections) if chunker == "structure" else _fixed_chunks(sections)
        )
        self.corpus_version = _corpus_version(sections)
        self.index_version = _index_version(self.chunks, self.chunker_version)
        self._tokens = tuple(_tokens(chunk.searchable_text) for chunk in self.chunks)
        self._term_frequencies = tuple(Counter(tokens) for tokens in self._tokens)
        self._document_frequencies = _document_frequencies(self._tokens)
        self._average_length = sum(map(len, self._tokens)) / len(self._tokens)
        self._dense_features = tuple(_dense_features(tokens) for tokens in self._tokens)
        self._dense_document_frequencies = _feature_document_frequencies(self._dense_features)
        self._dense_vectors = tuple(
            _dense_vector(features, self._dense_document_frequencies, len(self.chunks))
            for features in self._dense_features
        )

    def search(
        self,
        query: str,
        *,
        method: SearchMethod = "hybrid",
        limit: int = 10,
    ) -> SearchOutcome:
        normalized_query = " ".join(query.split())
        if len(normalized_query) < 3:
            raise ValueError("Search query must contain at least three characters")
        if limit < 1 or limit > 50:
            raise ValueError("Search limit must be between 1 and 50")
        query_tokens = _tokens(normalized_query)
        bm25_scores = self._bm25_scores(query_tokens)
        dense_scores = self._dense_scores(query_tokens)
        if method == "bm25":
            scores = self._apply_quality_adjustments(bm25_scores)
        elif method == "dense":
            scores = self._apply_quality_adjustments(dense_scores)
        elif method == "hybrid":
            scores = self._apply_quality_adjustments(
                _reciprocal_rank_fusion(bm25_scores, dense_scores)
            )
        else:
            scores = self._reranker_scores(normalized_query, query_tokens)
        ranking_query_tokens = (
            _semantic_query_tokens(query_tokens, _mentioned_documents(normalized_query))
            if method == "hybrid_rerank"
            else query_tokens
        )
        ranked = self._ranked_indices(
            scores,
            bm25_scores,
            dense_scores,
            query_tokens=ranking_query_tokens,
            query=normalized_query,
            diversify=method == "hybrid_rerank",
            limit=limit,
        )
        hits = tuple(
            self._hit(
                rank,
                index,
                scores[index],
                bm25_scores[index],
                dense_scores[index],
            )
            for rank, index in enumerate(ranked, start=1)
            if scores[index] > 0
        )
        return SearchOutcome(
            query=normalized_query,
            method=method,
            hits=hits,
            corpus_version=self.corpus_version,
            index_version=self.index_version,
            retrieval_version=RETRIEVAL_VERSION,
            bm25_version=BM25_VERSION,
            dense_version=DENSE_VERSION,
            hybrid_version=HYBRID_VERSION,
            reranker_version=RERANKER_VERSION,
            chunker_version=self.chunker_version,
        )

    def _reranker_scores(
        self,
        query: str,
        query_tokens: tuple[str, ...],
    ) -> tuple[float, ...]:
        mentioned_documents = _mentioned_documents(query)
        semantic_query_tokens = _semantic_query_tokens(query_tokens, mentioned_documents)
        query_terms = set(semantic_query_tokens)
        bm25_scores = self._bm25_scores(semantic_query_tokens)
        dense_scores = self._dense_scores(semantic_query_tokens)
        fused_scores = _reciprocal_rank_fusion(bm25_scores, dense_scores)
        term_weights = {
            term: math.log(1 + len(self.chunks) / (1 + self._document_frequencies.get(term, 0)))
            for term in query_terms
        }
        total_weight = sum(term_weights.values()) or 1.0
        max_fused = max(fused_scores) or 1.0
        max_bm25 = max(bm25_scores) or 1.0
        max_dense = max(dense_scores) or 1.0
        reranked: list[float] = []
        for index, chunk in enumerate(self.chunks):
            matched = query_terms & set(self._tokens[index])
            coverage = sum(term_weights[term] for term in matched) / total_weight
            document_score = 0.0
            if mentioned_documents:
                document_score = 1.0 if chunk.document_id in mentioned_documents else -0.5
            score = (
                0.25 * fused_scores[index] / max_fused
                + 0.20 * bm25_scores[index] / max_bm25
                + 0.10 * max(0.0, dense_scores[index]) / max_dense
                + 0.40 * coverage
                + 0.05 * document_score
            )
            if chunk.is_explanation or _is_empty_explanation(chunk.text):
                score *= 0.2
            if len(mentioned_documents) == 1 and chunk.document_id not in mentioned_documents:
                score *= 0.35
            reranked.append(score)
        return tuple(reranked)

    def _ranked_indices(
        self,
        scores: tuple[float, ...],
        bm25_scores: tuple[float, ...],
        dense_scores: tuple[float, ...],
        *,
        query_tokens: tuple[str, ...],
        query: str,
        diversify: bool,
        limit: int,
    ) -> list[int]:
        candidates = sorted(
            range(len(scores)),
            key=lambda index: (
                -scores[index],
                -bm25_scores[index],
                -dense_scores[index],
                index,
            ),
        )
        if not diversify:
            return candidates[:limit]

        selected: list[int] = []
        covered_terms: set[str] = set()
        covered_documents: set[str] = set()
        query_terms = set(query_tokens)
        mentioned_documents = _mentioned_documents(query)
        while candidates and len(selected) < limit:
            choice = max(
                candidates,
                key=lambda index: (
                    scores[index]
                    + 0.25
                    * len((query_terms & set(self._tokens[index])) - covered_terms)
                    / max(1, len(query_terms))
                    + (
                        0.08
                        if len(mentioned_documents) > 1
                        and self.chunks[index].document_id in mentioned_documents
                        and self.chunks[index].document_id not in covered_documents
                        else 0.0
                    ),
                    bm25_scores[index],
                    dense_scores[index],
                    -index,
                ),
            )
            candidates.remove(choice)
            if scores[choice] <= 0:
                break
            selected.append(choice)
            covered_terms.update(query_terms & set(self._tokens[choice]))
            covered_documents.add(self.chunks[choice].document_id)
        return selected

    def _apply_quality_adjustments(self, scores: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(
            score * (0.2 if chunk.is_explanation or _is_empty_explanation(chunk.text) else 1.0)
            for score, chunk in zip(scores, self.chunks, strict=True)
        )

    def _bm25_scores(self, query_tokens: tuple[str, ...]) -> tuple[float, ...]:
        query_terms = set(query_tokens)
        count = len(self.chunks)
        scores: list[float] = []
        for tokens, frequencies in zip(self._tokens, self._term_frequencies, strict=True):
            score = 0.0
            length_normalization = 1 - 0.75 + 0.75 * len(tokens) / self._average_length
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self._document_frequencies.get(term, 0)
                inverse_frequency = math.log(
                    1 + (count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                score += inverse_frequency * (
                    frequency * 2.5 / (frequency + 1.5 * length_normalization)
                )
            scores.append(score)
        return tuple(scores)

    def _dense_scores(self, query_tokens: tuple[str, ...]) -> tuple[float, ...]:
        query_vector = _dense_vector(
            _dense_features(query_tokens),
            self._dense_document_frequencies,
            len(self.chunks),
        )
        return tuple(_dot(query_vector, vector) for vector in self._dense_vectors)

    def _hit(
        self,
        rank: int,
        index: int,
        score: float,
        bm25_score: float,
        dense_score: float,
    ) -> SearchHit:
        chunk = self.chunks[index]
        excerpt = " ".join(chunk.text.split())
        if len(excerpt) > 360:
            excerpt = f"{excerpt[:357]}..."
        return SearchHit(
            rank=rank,
            chunk_id=chunk.chunk_id,
            section_ids=chunk.section_ids,
            document_id=chunk.document_id,
            document_version_id=chunk.document_version_id,
            document_title=chunk.document_title,
            document_status=chunk.document_status,
            heading=chunk.heading,
            excerpt=excerpt,
            source_url=chunk.source_url,
            source_anchor=chunk.source_anchor,
            score=score,
            bm25_score=bm25_score,
            dense_score=dense_score,
            status_checked_at=chunk.status_checked_at,
        )


def _tokens(text: str) -> tuple[str, ...]:
    normalized = text.casefold()
    normalized = re.sub(r"\bsebagaimana\s+dimaksud\b", "rujukan", normalized)
    normalized = re.sub(r"\byang\s+dimaksud\s+dengan\b", "definisi", normalized)
    return tuple(
        SYNONYM_LOOKUP.get(token, token)
        for token in TOKEN_PATTERN.findall(normalized)
        if len(token) > 1 and token not in STOPWORDS
    )


def _document_frequencies(documents: tuple[tuple[str, ...], ...]) -> dict[str, int]:
    frequencies: dict[str, int] = defaultdict(int)
    for tokens in documents:
        for token in set(tokens):
            frequencies[token] += 1
    return dict(frequencies)


def _dense_features(tokens: tuple[str, ...]) -> dict[str, float]:
    features: dict[str, float] = defaultdict(float)
    for token in tokens:
        features[token] += 1.0
    for token in tokens:
        padded = f"^{token}$"
        for width in (3, 4):
            for index in range(max(0, len(padded) - width + 1)):
                features[f"ng:{padded[index : index + width]}"] += 0.2
    return dict(features)


def _feature_document_frequencies(documents: tuple[dict[str, float], ...]) -> dict[str, int]:
    frequencies: dict[str, int] = defaultdict(int)
    for features in documents:
        for feature in features:
            frequencies[feature] += 1
    return dict(frequencies)


def _dense_vector(
    features: dict[str, float], document_frequencies: dict[str, int], document_count: int
) -> dict[int, float]:
    vector: dict[int, float] = defaultdict(float)
    for feature, frequency in features.items():
        digest = hashlib.sha256(feature.encode()).digest()
        dimension = int.from_bytes(digest[:2], "big") % 2048
        idf = math.log(1 + document_count / (1 + document_frequencies.get(feature, 0)))
        vector[dimension] += math.log1p(float(frequency)) * idf
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {dimension: value / norm for dimension, value in vector.items()}


def _dot(left: dict[int, float], right: dict[int, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(dimension, 0.0) for dimension, value in left.items())


def _reciprocal_rank_fusion(
    bm25_scores: tuple[float, ...], dense_scores: tuple[float, ...]
) -> tuple[float, ...]:
    fused = [0.0] * len(bm25_scores)
    for scores in (bm25_scores, dense_scores):
        ranking = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        for rank, index in enumerate(ranking, start=1):
            if scores[index] > 0:
                fused[index] += 1 / (60 + rank)
    return tuple(fused)


def _structure_chunks(sections: tuple[SourceSection, ...]) -> tuple[RetrievalChunk, ...]:
    chunks: list[RetrievalChunk] = []
    by_document: dict[str, list[SourceSection]] = defaultdict(list)
    for section in sections:
        by_document[section.document_id].append(section)
    for document_sections in by_document.values():
        current: list[SourceSection] = []
        current_is_explanation = False
        explanation_mode = False
        highest_pasal = 0
        for section in document_sections:
            pasal_match = re.match(r"^pasal\s+(\d+)\b", section.heading, re.IGNORECASE)
            is_pasal = pasal_match is not None
            is_ayat = bool(re.match(r"^\(\d+\)\b", section.heading))
            current_is_pasal = bool(
                current and re.match(r"^pasal\s+\d+\b", current[0].heading, re.IGNORECASE)
            )
            if is_pasal:
                pasal_number = int(pasal_match.group(1)) if pasal_match is not None else 0
                if highest_pasal >= 20 and pasal_number <= 5:
                    explanation_mode = True
                highest_pasal = max(highest_pasal, pasal_number)
                if current:
                    chunks.append(
                        _legal_structure_chunk(
                            current,
                            is_explanation=current_is_explanation,
                        )
                    )
                current = [section]
                current_is_explanation = explanation_mode
            elif current_is_pasal and is_ayat:
                current.append(section)
            else:
                if current:
                    chunks.append(
                        _legal_structure_chunk(
                            current,
                            is_explanation=current_is_explanation,
                        )
                    )
                current = [section]
                current_is_explanation = explanation_mode
        if current:
            chunks.append(
                _legal_structure_chunk(
                    current,
                    is_explanation=current_is_explanation,
                )
            )
    return tuple(chunks)


def _legal_structure_chunk(
    sections: list[SourceSection], *, is_explanation: bool
) -> RetrievalChunk:
    first, last = sections[0], sections[-1]
    return RetrievalChunk(
        chunk_id=first.section_id,
        section_ids=tuple(section.section_id for section in sections),
        document_id=first.document_id,
        document_version_id=first.document_version_id,
        manifest_version=first.manifest_version,
        document_title=first.document_title,
        document_status=first.document_status,
        heading=first.heading,
        text="\n".join(section.text for section in sections),
        source_url=first.source_url,
        source_anchor=(
            first.source_anchor
            if first.source_anchor == last.source_anchor
            else f"{first.source_anchor}..{last.source_anchor}"
        ),
        is_explanation=is_explanation,
        status_checked_at=first.status_checked_at,
    )


def _is_empty_explanation(text: str) -> bool:
    normalized = " ".join(text.casefold().split())
    return "cukup jelas" in normalized and len(normalized) < 240


def _mentioned_documents(query: str) -> set[str]:
    normalized = query.casefold()
    mentioned: set[str] = set()
    if re.search(r"\buu\b|undang[- ]undang|\b27\s*(?:/|tahun)\s*2022\b|\bpdp\b", normalized):
        mentioned.add("uu-27-2022")
    if re.search(r"\bpp\b|peraturan pemerintah|\b71\s*(?:/|tahun)\s*2019\b", normalized):
        mentioned.add("pp-71-2019")
    if re.search(r"permenkominfo|peraturan menteri|\b20\s*(?:/|tahun)\s*2016\b", normalized):
        mentioned.add("permenkominfo-20-2016")
    return mentioned


def _semantic_query_tokens(
    query_tokens: tuple[str, ...], mentioned_documents: set[str]
) -> tuple[str, ...]:
    excluded = {
        "bandingkan",
        "cari",
        "corpus",
        "dokumen",
        "jelaskan",
        "nomor",
        "pdp",
        "peraturan",
        "permenkominfo",
        "pp",
        "rangkum",
        "regulasi",
        "sebutkan",
        "tahun",
        "tunjukkan",
        "uu",
        "undang",
    }
    if mentioned_documents:
        excluded.update({"20", "27", "71", "2016", "2019", "2022"})
    semantic = tuple(token for token in query_tokens if token not in excluded)
    return semantic or query_tokens


def _fixed_chunks(sections: tuple[SourceSection, ...]) -> tuple[RetrievalChunk, ...]:
    chunks: list[RetrievalChunk] = []
    by_document: dict[str, list[SourceSection]] = defaultdict(list)
    for section in sections:
        by_document[section.document_id].append(section)
    for document_sections in by_document.values():
        current: list[SourceSection] = []
        current_length = 0
        for section in document_sections:
            section_length = len(section.text)
            if current and current_length + section_length > 1600:
                chunks.append(_fixed_chunk(current))
                current = []
                current_length = 0
            current.append(section)
            current_length += section_length
        if current:
            chunks.append(_fixed_chunk(current))
    return tuple(chunks)


def _fixed_chunk(sections: list[SourceSection]) -> RetrievalChunk:
    first, last = sections[0], sections[-1]
    identity = ":".join(section.section_id for section in sections)
    return RetrievalChunk(
        chunk_id=hashlib.sha256(identity.encode()).hexdigest()[:24],
        section_ids=tuple(section.section_id for section in sections),
        document_id=first.document_id,
        document_version_id=first.document_version_id,
        manifest_version=first.manifest_version,
        document_title=first.document_title,
        document_status=first.document_status,
        heading=f"{first.heading} — {last.heading}",
        text="\n".join(section.text for section in sections),
        source_url=first.source_url,
        source_anchor=f"{first.source_anchor}..{last.source_anchor}",
        status_checked_at=first.status_checked_at,
    )


def _corpus_version(sections: tuple[SourceSection, ...]) -> str:
    versions = sorted({section.manifest_version for section in sections})
    return "+".join(versions)


def _index_version(chunks: tuple[RetrievalChunk, ...], chunker_version: str) -> str:
    identity = {
        "retrieval": RETRIEVAL_VERSION,
        "chunker": chunker_version,
        "chunks": [
            [chunk.chunk_id, chunk.document_version_id, list(chunk.section_ids)] for chunk in chunks
        ],
    }
    encoded = repr(identity).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]
