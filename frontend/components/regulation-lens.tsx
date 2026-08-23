"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { AnimatedNumber, EmptyState, WorkspaceSkeleton, WorkspaceTabs, WorkspaceToast } from "./workspace-ui";

type RegulationTab = "answer" | "evidence" | "compare";

interface Version {
  id: string;
  manifest_version: string;
  retrieved_at: string;
  parser_status: string;
  section_count: number;
  published: boolean;
}

interface Regulation {
  document_id: string;
  document_type: string;
  number: string;
  year: number;
  title: string;
  status: string;
  status_checked_at: string;
  source_page_url: string;
  latest_version: Version | null;
}

interface Citation {
  citation_id: string;
  section_ids: string[];
  document_id: string;
  document_version_id: string;
  document_title: string;
  document_status: string;
  heading: string;
  quote: string;
  source_url: string;
  source_anchor: string;
  status_checked_at: string | null;
}

interface Answer {
  answerable: boolean;
  answer: string;
  confidence: "high" | "medium" | "low";
  evidence_coverage: number;
  refusal_reason: string | null;
  citations: Citation[];
  disclaimer: string;
  pipeline_version: string;
  provenance: {
    corpus_version: string;
    index_version: string;
    retrieved_evidence_count: number;
  };
}

interface SectionContext {
  selected_section_id: string;
  document_title: string;
  document_status: string;
  status_checked_at: string;
  source_url: string;
  sections: Array<{
    section_id: string;
    heading: string;
    text: string;
    source_anchor: string;
  }>;
}

interface Comparison {
  comparison_version: string;
  counts: { added: number; removed: number; modified: number };
  unchanged_count: number;
  disclaimer: string;
  changes: Array<{
    change_type: "added" | "removed" | "modified";
    heading: string;
    summary: string;
    base: { text: string; source_anchor: string } | null;
    target: { text: string; source_anchor: string } | null;
  }>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function dateLabel(value: string | null | undefined): string {
  if (!value) return "Tanggal belum tersedia";
  return new Intl.DateTimeFormat("id-ID", { dateStyle: "medium" }).format(new Date(value));
}

export function RegulationLens() {
  const [documents, setDocuments] = useState<Regulation[]>([]);
  const [question, setQuestion] = useState("Apa hak akses dan salinan Data Pribadi?");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [context, setContext] = useState<SectionContext | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [versions, setVersions] = useState<Version[]>([]);
  const [baseVersion, setBaseVersion] = useState("");
  const [targetVersion, setTargetVersion] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<RegulationTab>("answer");
  const [corpusOpen, setCorpusOpen] = useState(true);
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);
  const [selectedChangeIndex, setSelectedChangeIndex] = useState(0);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const storedQuestion = window.localStorage.getItem("nusa-intel-regulation-question");
    const requestedQuestion = params.get("q") ?? storedQuestion;
    if (requestedQuestion && requestedQuestion.length >= 8 && requestedQuestion.length <= 500) {
      queueMicrotask(() => setQuestion(requestedQuestion));
    }
  }, []);

  useEffect(() => {
    if (question.trim().length >= 8) {
      window.localStorage.setItem("nusa-intel-regulation-question", question);
    }
  }, [question]);

  useEffect(() => {
    let active = true;
    void fetchJson<{ items: Regulation[] }>("/api/v1/regulations")
      .then((payload) => {
        if (!active) return;
        setDocuments(payload.items);
        setDocumentId(payload.items[0]?.document_id ?? "");
      })
      .catch(() => active && setMessage("Corpus regulasi belum dapat dimuat."))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!documentId) return;
    let active = true;
    void fetchJson<{ items: Version[] }>(`/api/v1/regulations/${documentId}/versions`)
      .then((payload) => {
        if (!active) return;
        setVersions(payload.items);
        setBaseVersion(payload.items[1]?.id ?? "");
        setTargetVersion(payload.items[0]?.id ?? "");
        setComparison(null);
      })
      .catch(() => active && setVersions([]));
    return () => {
      active = false;
    };
  }, [documentId]);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (question.trim().length < 8) return;
    setRunning(true);
    setMessage(null);
    setAnswer(null);
    setContext(null);
    try {
      const result = await fetchJson<Answer>("/api/v1/regulations/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, maximum_citations: 5 }),
      });
      setAnswer(result);
      setActiveCitationId(result.citations[0]?.citation_id ?? null);
      setActiveTab("answer");
      setMessage(result.answerable ? "Jawaban selesai. Evidence citation tersedia pada tab Evidence." : "Pertanyaan ditolak sesuai batas corpus.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Jawaban tidak dapat dibuat.");
    } finally {
      setRunning(false);
    }
  }

  async function openContext(citation: Citation) {
    const sectionId = citation.section_ids[0];
    if (!sectionId) return;
    setMessage(null);
    try {
      const result = await fetchJson<SectionContext>(
        `/api/v1/regulations/${citation.document_id}/sections/${sectionId}/context?` +
          new URLSearchParams({ version_id: citation.document_version_id, before: "2", after: "2" }),
      );
      setContext(result);
      setActiveCitationId(citation.citation_id);
      setActiveTab("evidence");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Konteks citation tidak dapat dibuka.");
    }
  }

  async function compare() {
    if (!documentId || !baseVersion || !targetVersion || baseVersion === targetVersion) return;
    setMessage(null);
    try {
      const query = new URLSearchParams({
        document_id: documentId,
        base_version_id: baseVersion,
        target_version_id: targetVersion,
      });
      setComparison(await fetchJson<Comparison>(`/api/v1/regulations/compare?${query}`));
      setSelectedChangeIndex(0);
      setMessage("Perbandingan versi selesai.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Versi tidak dapat dibandingkan.");
    }
  }

  async function shareQuestion() {
    const query = new URLSearchParams({ q: question.trim() });
    window.history.replaceState(null, "", `${window.location.pathname}?${query}`);
    try {
      await navigator.clipboard?.writeText(window.location.href);
      setMessage("Tautan pertanyaan disalin.");
    } catch {
      setMessage("Pertanyaan tersimpan pada URL halaman.");
    }
  }

  const activeCitation = useMemo(
    () => answer?.citations.find((citation) => citation.citation_id === activeCitationId) ?? answer?.citations[0] ?? null,
    [activeCitationId, answer],
  );
  const activeChange = comparison?.changes[selectedChangeIndex] ?? comparison?.changes[0] ?? null;

  function showCitation(citationId: string) {
    setActiveCitationId(citationId);
    setActiveTab("evidence");
    window.setTimeout(() => {
      const card = document.querySelector<HTMLElement>(`[data-citation-id="${citationId}"]`);
      card?.scrollIntoView?.({ behavior: "smooth", block: "center" });
    }, 0);
  }

  function renderGroundedLine(line: string, lineIndex: number) {
    const parts = line.split(/(\[C\d+\])/g);
    return (
      <p key={`${line}-${lineIndex}`} style={{ animationDelay: `${lineIndex * 90}ms` }}>
        {parts.map((part, index) => {
          const match = part.match(/^\[(C\d+)\]$/);
          if (!match) return part;
          const citationId = match[1];
          const exists = answer?.citations.some((citation) => citation.citation_id === citationId);
          return exists ? (
            <button
              type="button"
              className="citation-reference"
              key={`${part}-${index}`}
              onClick={() => showCitation(citationId)}
              onPointerEnter={() => setActiveCitationId(citationId)}
              onFocus={() => setActiveCitationId(citationId)}
              aria-label={`Buka citation ${citationId}`}
            >{part}</button>
          ) : part;
        })}
      </p>
    );
  }

  return (
    <section className="regulation-shell" id="regulasilens" aria-labelledby="regulation-title">
      <div className="regulation-header">
        <div>
          <p className="kicker">Release 0.6 / RegulasiLens beta</p>
          <h2 id="regulation-title">Jawaban hukum berhenti ketika buktinya berhenti.</h2>
          <p>
            Setiap klaim berasal dari evidence retrieval, setiap citation dapat dibuka, dan pertanyaan
            di luar corpus akan ditolak.
          </p>
        </div>
        <div className="regulation-gate" aria-label="Grounding guarantees">
          <strong>0%</strong>
          <span>fabricated citation pada benchmark</span>
          <small>evidence-extractive-id-v1</small>
        </div>
      </div>

      <div className="workspace-config-toggle corpus-toggle">
        <div><span>Corpus aktif</span><strong>{documents.length} dokumen · status dan versi terlacak</strong></div>
        <button type="button" onClick={() => setCorpusOpen((current) => !current)} aria-expanded={corpusOpen}>
          {corpusOpen ? "Sembunyikan corpus" : "Lihat corpus"}
        </button>
      </div>

      <div className="regulation-catalog" aria-label="Corpus regulasi" hidden={!corpusOpen}>
        {loading && <WorkspaceSkeleton label="Memuat corpus regulasi" />}
        {!loading && !documents.length && <p>Belum ada dokumen terpublikasi.</p>}
        {documents.map((document) => (
          <article key={document.document_id}>
            <span className="regulation-status">{document.status}</span>
            <h3>{document.document_type} {document.number}/{document.year}</h3>
            <p>{document.title}</p>
            <small>
              Status diperiksa {dateLabel(document.status_checked_at)} · corpus {document.latest_version?.manifest_version ?? "—"}
            </small>
          </article>
        ))}
      </div>

      <WorkspaceTabs
        label="Area RegulasiLens"
        active={activeTab}
        onChange={setActiveTab}
        tabs={[
          { id: "answer", label: "Pencarian & Jawaban" },
          { id: "evidence", label: "Evidence", count: answer?.citations.length ?? 0 },
          { id: "compare", label: "Perbandingan", count: versions.length },
        ]}
      />

      <div className="regulation-workspace" hidden={activeTab !== "answer"}>
        <form className="answer-panel" onSubmit={ask}>
          <label htmlFor="regulation-question">Pertanyaan berbasis corpus</label>
          <textarea
            id="regulation-question"
            value={question}
            minLength={8}
            maxLength={500}
            onChange={(event) => setQuestion(event.target.value)}
          />
          <div className="answer-actions">
            <small>{question.length}/500 karakter · maksimum 5 citation</small>
            <button type="button" className="secondary-button" onClick={() => void shareQuestion()} disabled={question.trim().length < 8}>Salin pertanyaan</button>
            <button type="submit" disabled={running || question.trim().length < 8}>
              {running ? "Memeriksa evidence..." : "Jawab dengan bukti"}
            </button>
          </div>
        </form>

        <div className="answer-output" aria-live="polite">
          {!answer && !message && <p className="empty-copy">Jawaban dan refusal akan muncul di sini.</p>}
          {answer && (
            <>
              <div className="answer-meta">
                <span>{answer.answerable ? "ANSWERABLE" : "REFUSED"}</span>
                <span>confidence {answer.confidence}</span>
                <span>coverage {Math.round(answer.evidence_coverage * 100)}%</span>
              </div>
              <div className={answer.answerable ? "grounded-answer" : "refusal-answer"}>
                {answer.answer.split("\n").map(renderGroundedLine)}
                {answer.refusal_reason && <small>{answer.refusal_reason}</small>}
              </div>
              <p className="regulation-disclaimer">{answer.disclaimer}</p>
              <small className="provenance-line">
                Corpus {answer.provenance.corpus_version} · index {answer.provenance.index_version}
              </small>
            </>
          )}
        </div>
      </div>

      <div className="evidence-workspace" hidden={activeTab !== "evidence"}>
      {answer?.citations.length ? (
        <>
        {activeCitation && (
          <div className="evidence-link-strip" aria-live="polite">
            <i aria-hidden="true" />
            <span>Klaim aktif</span>
            <strong>Citation {activeCitation.citation_id} · {activeCitation.heading}</strong>
            <small>{activeCitation.document_title}</small>
          </div>
        )}
        <div className="citation-grid" aria-label="Citation evidence">
          {answer.citations.map((citation) => (
            <article
              key={citation.citation_id}
              data-citation-id={citation.citation_id}
              data-active={activeCitation?.citation_id === citation.citation_id}
              data-tilt
              onPointerEnter={() => setActiveCitationId(citation.citation_id)}
            >
              <div className="citation-heading">
                <strong>[{citation.citation_id}] {citation.heading}</strong>
                <span>{citation.document_status}</span>
              </div>
              <blockquote>{citation.quote}</blockquote>
              <p>{citation.document_title}</p>
              <small>Status diperiksa {dateLabel(citation.status_checked_at)}</small>
              <div className="citation-actions">
                <button type="button" onClick={() => void openContext(citation)}>Buka konteks</button>
                <a href={citation.source_url} target="_blank" rel="noreferrer">Dokumen resmi</a>
              </div>
            </article>
          ))}
        </div>
        </>
      ) : (
        <EmptyState
          eyebrow="Belum ada evidence"
          title="Ajukan pertanyaan terlebih dahulu"
          description="Citation, kutipan sumber, dan konteks pasal akan dikumpulkan di area ini."
        />
      )}

      {context && (
        <aside className="context-viewer" aria-labelledby="context-title">
          <div className="context-heading">
            <div>
              <p className="kicker">Surrounding context</p>
              <h3 id="context-title">{context.document_title}</h3>
            </div>
            <button type="button" onClick={() => setContext(null)}>Tutup konteks</button>
          </div>
          {context.sections.map((section) => (
            <article className={section.section_id === context.selected_section_id ? "selected" : ""} key={section.section_id}>
              <strong>{section.heading}</strong>
              <p>{section.text}</p>
              <small>{section.source_anchor}</small>
            </article>
          ))}
        </aside>
      )}
      </div>

      <div className="version-compare" hidden={activeTab !== "compare"}>
        <div>
          <p className="kicker">Structured version comparison</p>
          <h3>Perubahan hanya diringkas jika teks sumber tersedia.</h3>
        </div>
        <div className="compare-controls">
          <label>Dokumen
            <select value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
              {documents.map((document) => <option key={document.document_id} value={document.document_id}>{document.document_id}</option>)}
            </select>
          </label>
          <label>Versi dasar
            <select value={baseVersion} onChange={(event) => setBaseVersion(event.target.value)}>
              <option value="">Pilih versi</option>
              {versions.map((version) => <option key={version.id} value={version.id}>{dateLabel(version.retrieved_at)}</option>)}
            </select>
          </label>
          <label>Versi target
            <select value={targetVersion} onChange={(event) => setTargetVersion(event.target.value)}>
              <option value="">Pilih versi</option>
              {versions.map((version) => <option key={version.id} value={version.id}>{dateLabel(version.retrieved_at)}</option>)}
            </select>
          </label>
          <button type="button" onClick={() => void compare()} disabled={!baseVersion || !targetVersion || baseVersion === targetVersion}>
            Bandingkan versi
          </button>
        </div>
        {versions.length < 2 && <p className="empty-copy">Perbandingan aktif setelah sedikitnya dua versi dokumen tersimpan.</p>}
        {comparison && (
          <div className="comparison-result">
            <div className="comparison-counts">
              <span data-change="added"><AnimatedNumber value={comparison.counts.added} initialFrom={0} /> ditambah</span>
              <span data-change="removed"><AnimatedNumber value={comparison.counts.removed} initialFrom={0} /> dihapus</span>
              <span data-change="modified"><AnimatedNumber value={comparison.counts.modified} initialFrom={0} /> diubah</span>
              <span data-change="unchanged"><AnimatedNumber value={comparison.unchanged_count} initialFrom={0} /> tetap</span>
            </div>
            {activeChange ? (
              <div className="diff-explorer">
                <nav aria-label="Daftar perubahan versi">
                  {comparison.changes.map((change, index) => (
                    <button
                      type="button"
                      key={`${change.heading}-${index}`}
                      data-active={selectedChangeIndex === index}
                      data-change={change.change_type}
                      aria-pressed={selectedChangeIndex === index}
                      onClick={() => setSelectedChangeIndex(index)}
                    >
                      <span>{change.change_type}</span>
                      <strong>{change.heading}</strong>
                    </button>
                  ))}
                </nav>
                <article className="diff-stage" data-change={activeChange.change_type}>
                  <div className="diff-stage-heading">
                    <span>{activeChange.change_type.toUpperCase()}</span>
                    <div><strong>{activeChange.heading}</strong><p>{activeChange.summary}</p></div>
                  </div>
                  <div className="comparison-texts">
                    <section data-side="base"><span>Versi dasar</span><pre>{activeChange.base?.text ?? "— tidak ada pada versi dasar —"}</pre></section>
                    <section data-side="target"><span>Versi target</span><pre>{activeChange.target?.text ?? "— tidak ada pada versi target —"}</pre></section>
                  </div>
                </article>
              </div>
            ) : <p className="empty-copy">Tidak ada perubahan tekstual pada dua versi ini.</p>}
            <p className="regulation-disclaimer">{comparison.disclaimer}</p>
          </div>
        )}
      </div>
      {running && <div className="analysis-progress" role="status"><i /><span>Menelusuri corpus dan memeriksa evidence…</span></div>}
      <WorkspaceToast message={message} tone={message?.toLowerCase().includes("tidak dapat") ? "error" : "info"} onDismiss={() => setMessage(null)} />
    </section>
  );
}
