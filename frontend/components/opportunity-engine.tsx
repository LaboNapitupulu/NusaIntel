"use client";

import type { CSSProperties } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { EmptyState, WorkspaceSkeleton, WorkspaceTabs, WorkspaceToast } from "./workspace-ui";

type Normalization = "min_max" | "percentile";
type Direction = "higher" | "lower";
type ViewState = "loading" | "ready" | "empty" | "error";
type SetupStep = 1 | 2 | 3 | 4;
type ResultTab = "ranking" | "comparison" | "trend" | "sensitivity" | "methodology";

interface Indicator {
  code: string;
  name: string;
  definition: string;
  unit: string;
  favorable_direction: Direction;
  source_url: string;
  reference_period_rule: string;
  quality_status: "healthy" | "warning" | "critical";
  dataset_version_id: string | null;
  periods: Array<{ period: string; coverage_percent: number }>;
}

interface Region {
  code: string;
  name: string;
}

interface WeightState {
  code: string;
  weight: number;
  direction: Direction;
}

interface ComparisonResponse {
  year: number;
  normalization: Normalization;
  methodology_version: string;
  regions: Array<{
    region_code: string;
    region_name: string;
    values: Array<{
      indicator_code: string;
      raw_value: number | null;
      normalized_value: number | null;
      unit: string;
      reference_period: string;
      missing: boolean;
    }>;
  }>;
  trends: Array<{
    indicator_code: string;
    region_code: string;
    region_name: string;
    period: string;
    value: number | null;
    unit: string;
  }>;
  distributions: Record<
    string,
    { count: number; minimum: number | null; median: number | null; maximum: number | null }
  >;
  dataset_versions: Record<
    string,
    { version_id: string; checksum: string; analysis_reference_period: string }
  >;
  sources: Record<string, { name: string; url: string; attribution: string }>;
}

interface Contribution {
  indicator_code: string;
  raw_value: number | null;
  normalized_value: number | null;
  configured_weight: number;
  effective_weight: number | null;
  contribution: number | null;
  direction: Direction;
  missing: boolean;
}

interface ScoreRow {
  region_code: string;
  region_name: string;
  coverage: number;
  eligible: boolean;
  score: number | null;
  rank: number | null;
  contributions: Contribution[];
}

interface ScoreResponse {
  methodology_version: string;
  results: ScoreRow[];
  dataset_versions: ComparisonResponse["dataset_versions"];
}

interface SensitivityResponse {
  scenario_count: number;
  perturbation: number;
  disclaimer: string;
  stability: Array<{
    region_code: string;
    region_name: string;
    base_rank: number | null;
    min_rank: number | null;
    max_rank: number | null;
    max_absolute_shift: number | null;
    unchanged_percent: number | null;
  }>;
}

interface ScenarioState {
  regionCodes: string[];
  weights: WeightState[];
  year: number;
  normalization: Normalization;
  coverageThreshold: number;
  perturbation: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const preferredIndicators = ["tpt", "poverty_rate", "hdi"];

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function equalWeights(codes: string[], indicators: Indicator[]): WeightState[] {
  if (!codes.length) return [];
  const base = Math.floor((100 / codes.length) * 100) / 100;
  let remainder = Math.round((100 - base * codes.length) * 100) / 100;
  return codes.map((code, index) => {
    const addition = index === 0 ? remainder : 0;
    remainder = 0;
    return {
      code,
      weight: Math.round((base + addition) * 100) / 100,
      direction:
        indicators.find((indicator) => indicator.code === code)?.favorable_direction ?? "higher",
    };
  });
}

function rebalanceWeights(weights: WeightState[], changedCode: string, requestedWeight: number): WeightState[] {
  if (weights.length <= 1) return weights.map((item) => ({ ...item, weight: 100 }));
  const nextWeight = Math.min(100, Math.max(0, requestedWeight));
  const others = weights.filter((item) => item.code !== changedCode);
  const remaining = 100 - nextWeight;
  const otherTotal = others.reduce((total, item) => total + item.weight, 0);
  let distributed = 0;
  return weights.map((item) => {
    if (item.code === changedCode) return { ...item, weight: Math.round(nextWeight * 100) / 100 };
    const otherIndex = others.findIndex((candidate) => candidate.code === item.code);
    const isLast = otherIndex === others.length - 1;
    const proportional = otherTotal > 0 ? remaining * (item.weight / otherTotal) : remaining / others.length;
    const weight = isLast ? remaining - distributed : Math.round(proportional * 100) / 100;
    distributed += weight;
    return { ...item, weight: Math.round(weight * 100) / 100 };
  });
}

function commonYears(weights: WeightState[], indicators: Indicator[]): number[] {
  const selected = weights
    .map((weight) => indicators.find((indicator) => indicator.code === weight.code))
    .filter((indicator): indicator is Indicator => Boolean(indicator));
  if (!selected.length) return [];
  const first = selected[0].periods
    .filter((period) => Number(period.coverage_percent) > 0)
    .map((period) => Number(period.period.slice(0, 4)));
  return first
    .filter((year) =>
      selected.every((indicator) =>
        indicator.periods.some(
          (candidate) =>
            Number(candidate.period.slice(0, 4)) === year &&
            Number(candidate.coverage_percent) > 0,
        ),
      ),
    )
    .filter((year, index, years) => years.indexOf(year) === index)
    .sort((left, right) => right - left);
}

function scorePayload(scenario: ScenarioState) {
  return {
    region_codes: scenario.regionCodes,
    indicators: scenario.weights,
    year: scenario.year,
    normalization: scenario.normalization,
    coverage_threshold: scenario.coverageThreshold,
  };
}

function formatNumber(value: number | null, digits = 2): string {
  if (value === null || Number.isNaN(value)) return "Tidak tersedia";
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: digits }).format(value);
}

function qualityLabel(status: string): string {
  if (status === "healthy") return "Data siap";
  if (status === "warning") return "Perlu perhatian";
  if (status === "critical") return "Belum siap";
  return "Status belum tersedia";
}

function encodeScenario(scenario: ScenarioState): string {
  return btoa(JSON.stringify(scenario));
}

function decodeScenario(value: string | null): ScenarioState | null {
  if (!value) return null;
  try {
    const candidate = JSON.parse(atob(value)) as Partial<ScenarioState>;
    const validWeights =
      Array.isArray(candidate.weights) &&
      candidate.weights.length >= 1 &&
      candidate.weights.length <= 6 &&
      candidate.weights.every(
        (item) =>
          typeof item?.code === "string" &&
          typeof item.weight === "number" &&
          Number.isFinite(item.weight) &&
          (item.direction === "higher" || item.direction === "lower"),
      );
    const validRegions =
      Array.isArray(candidate.regionCodes) &&
      candidate.regionCodes.length >= 2 &&
      candidate.regionCodes.length <= 5 &&
      candidate.regionCodes.every((code) => typeof code === "string");
    if (
      !validWeights ||
      !validRegions ||
      !Number.isInteger(candidate.year) ||
      (candidate.normalization !== "min_max" && candidate.normalization !== "percentile") ||
      typeof candidate.coverageThreshold !== "number" ||
      candidate.coverageThreshold < 0 ||
      candidate.coverageThreshold > 1 ||
      typeof candidate.perturbation !== "number" ||
      candidate.perturbation <= 0 ||
      candidate.perturbation > 0.5
    ) {
      return null;
    }
    return candidate as ScenarioState;
  } catch {
    return null;
  }
}

export function OpportunityEngine() {
  const [state, setState] = useState<ViewState>("loading");
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [scenario, setScenario] = useState<ScenarioState>({
    regionCodes: [],
    weights: [],
    year: 0,
    normalization: "min_max",
    coverageThreshold: 1,
    perturbation: 0.1,
  });
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [setupStep, setSetupStep] = useState<SetupStep>(1);
  const [resultTab, setResultTab] = useState<ResultTab>("ranking");
  const [previewing, setPreviewing] = useState(false);
  const [livePreview, setLivePreview] = useState(false);
  const lastScoredFingerprint = useRef("");

  const initialize = useCallback(async () => {
    setState("loading");
    try {
      const [indicatorPayload, regionPayload] = await Promise.all([
        fetchJson<{ items: Indicator[] }>("/api/v1/opportunity/indicators"),
        fetchJson<{ items: Region[] }>("/api/v1/opportunity/regions"),
      ]);
      setIndicators(indicatorPayload.items);
      setRegions(regionPayload.items);
      if (!indicatorPayload.items.length || regionPayload.items.length < 2) {
        setState("empty");
        return;
      }
      const shared =
        decodeScenario(new URLSearchParams(window.location.search).get("scenario")) ??
        decodeScenario(window.localStorage.getItem("nusa-intel-opportunity-scenario"));
      const availableCodes = new Set(indicatorPayload.items.map((item) => item.code));
      const availableRegions = new Set(regionPayload.items.map((item) => item.code));
      if (
        shared &&
        shared.weights.every((item) => availableCodes.has(item.code)) &&
        shared.regionCodes.every((code) => availableRegions.has(code))
      ) {
        setScenario(shared);
      } else {
        const codes = preferredIndicators.filter((code) => availableCodes.has(code));
        const fallbackCodes = codes.length ? codes : indicatorPayload.items.slice(0, 3).map((item) => item.code);
        const nextWeights = equalWeights(fallbackCodes, indicatorPayload.items);
        setScenario({
          regionCodes: regionPayload.items.slice(0, 3).map((item) => item.code),
          weights: nextWeights,
          year: commonYears(nextWeights, indicatorPayload.items)[0] ?? 0,
          normalization: "min_max",
          coverageThreshold: 1,
          perturbation: 0.1,
        });
      }
      setState("ready");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    let active = true;
    void Promise.all([
      fetchJson<{ items: Indicator[] }>("/api/v1/opportunity/indicators"),
      fetchJson<{ items: Region[] }>("/api/v1/opportunity/regions"),
    ])
      .then(([indicatorPayload, regionPayload]) => {
        if (!active) return;
        setIndicators(indicatorPayload.items);
        setRegions(regionPayload.items);
        if (!indicatorPayload.items.length || regionPayload.items.length < 2) {
          setState("empty");
          return;
        }
        const shared =
          decodeScenario(new URLSearchParams(window.location.search).get("scenario")) ??
          decodeScenario(window.localStorage.getItem("nusa-intel-opportunity-scenario"));
        const availableCodes = new Set(indicatorPayload.items.map((item) => item.code));
        const availableRegions = new Set(regionPayload.items.map((item) => item.code));
        if (
          shared &&
          shared.weights.every((item) => availableCodes.has(item.code)) &&
          shared.regionCodes.every((code) => availableRegions.has(code))
        ) {
          setScenario(shared);
        } else {
          const codes = preferredIndicators.filter((code) => availableCodes.has(code));
          const fallbackCodes = codes.length
            ? codes
            : indicatorPayload.items.slice(0, 3).map((item) => item.code);
          const nextWeights = equalWeights(fallbackCodes, indicatorPayload.items);
          setScenario({
            regionCodes: regionPayload.items.slice(0, 3).map((item) => item.code),
            weights: nextWeights,
            year: commonYears(nextWeights, indicatorPayload.items)[0] ?? 0,
            normalization: "min_max",
            coverageThreshold: 1,
            perturbation: 0.1,
          });
        }
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, []);

  const years = useMemo(
    () => commonYears(scenario.weights, indicators),
    [scenario.weights, indicators],
  );
  const activeYear = years.includes(scenario.year) ? scenario.year : (years[0] ?? 0);
  const activeScenario = useMemo(
    () => ({ ...scenario, year: activeYear }),
    [activeYear, scenario],
  );
  const scenarioFingerprint = useMemo(() => JSON.stringify(scorePayload(activeScenario)), [activeScenario]);
  useEffect(() => {
    if (state !== "ready" || !scenario.regionCodes.length || !scenario.weights.length) return;
    window.localStorage.setItem("nusa-intel-opportunity-scenario", encodeScenario(activeScenario));
  }, [activeScenario, scenario.regionCodes.length, scenario.weights.length, state]);
  const weightTotal = scenario.weights.reduce((total, item) => total + item.weight, 0);
  const configurationValid =
    scenario.regionCodes.length >= 2 &&
    scenario.regionCodes.length <= 5 &&
    scenario.weights.length > 0 &&
    Math.abs(weightTotal - 100) <= 0.01 &&
    activeYear > 0;

  const runAnalysis = useCallback(async () => {
    if (!configurationValid) return;
    setRunning(true);
    setMessage(null);
    try {
      const payload = scorePayload(activeScenario);
      const [nextComparison, nextScore, nextSensitivity] = await Promise.all([
        fetchJson<ComparisonResponse>("/api/v1/opportunity/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            region_codes: activeScenario.regionCodes,
            indicator_codes: activeScenario.weights.map((item) => item.code),
            year: activeScenario.year,
            normalization: activeScenario.normalization,
          }),
        }),
        fetchJson<ScoreResponse>("/api/v1/opportunity/score", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }),
        fetchJson<SensitivityResponse>("/api/v1/opportunity/sensitivity", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...payload, perturbation: activeScenario.perturbation }),
        }),
      ]);
      setComparison(nextComparison);
      lastScoredFingerprint.current = scenarioFingerprint;
      setScore(nextScore);
      setSensitivity(nextSensitivity);
      setLivePreview(false);
      setResultTab("ranking");
      setMessage("Analisis selesai. Hasil perbandingan siap diperiksa.");
    } catch {
      setMessage("Analisis belum dapat dijalankan. Coba lagi.");
    } finally {
      setRunning(false);
    }
  }, [activeScenario, configurationValid, scenarioFingerprint]);

  useEffect(() => {
    if (!score || !configurationValid || scenarioFingerprint === lastScoredFingerprint.current) return;
    let active = true;
    setPreviewing(true);
    const timer = window.setTimeout(() => {
      void fetchJson<ScoreResponse>("/api/v1/opportunity/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scorePayload(activeScenario)),
      })
        .then((nextScore) => {
          if (!active) return;
          lastScoredFingerprint.current = scenarioFingerprint;
          setScore(nextScore);
          setResultTab("ranking");
          setLivePreview(true);
        })
        .catch(() => active && setMessage("Peringkat belum dapat diperbarui. Coba lagi."))
        .finally(() => active && setPreviewing(false));
    }, 450);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [activeScenario, configurationValid, scenarioFingerprint, score]);

  function toggleRegion(code: string) {
    setScenario((current) => {
      const selected = current.regionCodes.includes(code);
      if (!selected && current.regionCodes.length === 5) return current;
      return {
        ...current,
        regionCodes: selected
          ? current.regionCodes.filter((item) => item !== code)
          : [...current.regionCodes, code],
      };
    });
  }

  function toggleIndicator(code: string) {
    setScenario((current) => {
      const selected = current.weights.some((item) => item.code === code);
      if (!selected && current.weights.length === 6) return current;
      const codes = selected
        ? current.weights.filter((item) => item.code !== code).map((item) => item.code)
        : [...current.weights.map((item) => item.code), code];
      const nextWeights = equalWeights(codes, indicators);
      const nextYears = commonYears(nextWeights, indicators);
      return {
        ...current,
        weights: nextWeights,
        year: nextYears.includes(current.year) ? current.year : (nextYears[0] ?? 0),
      };
    });
  }

  async function shareScenario() {
    const parameters = new URLSearchParams(window.location.search);
    parameters.set("scenario", encodeScenario(activeScenario));
    const url = `${window.location.pathname}?${parameters.toString()}`;
    window.history.replaceState(null, "", url);
    try {
      await navigator.clipboard?.writeText(window.location.href);
      setMessage("Tautan skenario disalin. Tidak ada identitas pengguna yang disimpan.");
    } catch {
      setMessage("Skenario sudah tersimpan pada URL halaman ini.");
    }
  }

  async function exportReport() {
    try {
      const report = await fetchJson<Record<string, unknown>>("/api/v1/opportunity/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...scorePayload(activeScenario),
          perturbation: activeScenario.perturbation,
        }),
      });
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `nusa-intel-scenario-${activeScenario.year}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      setMessage("Hasil dan pilihan Anda berhasil diunduh.");
    } catch {
      setMessage("Hasil belum dapat diunduh. Coba lagi.");
    }
  }

  if (state === "loading") {
    return <section className="opportunity-shell opportunity-state"><WorkspaceSkeleton label="Memuat perbandingan wilayah" /></section>;
  }
  if (state === "error") {
    return (
      <section className="opportunity-shell opportunity-state">
        <p>Data wilayah belum dapat dimuat.</p>
        <button type="button" onClick={() => void initialize()}>
          Coba lagi
        </button>
      </section>
    );
  }
  if (state === "empty") {
    return (
      <section className="opportunity-shell opportunity-state">
        Belum ada data wilayah yang siap dibandingkan.
      </section>
    );
  }

  return (
    <section className="opportunity-shell" id="opportunity" aria-labelledby="opportunity-title">
      <header className="opportunity-header">
        <div>
          <p className="kicker">Perbandingan peluang regional</p>
          <h2 id="opportunity-title">Bandingkan wilayah tanpa menyembunyikan asumsi.</h2>
          <p>
            Tentukan wilayah dan prioritas Anda. Hasil menunjukkan bagaimana setiap pilihan
            memengaruhi urutan wilayah secara transparan.
          </p>
        </div>
        <div className="scenario-actions">
          <button type="button" className="secondary-button" onClick={() => void shareScenario()}>
            Salin skenario
          </button>
          <button type="button" className="secondary-button" onClick={() => void exportReport()} disabled={!score}>
            Unduh hasil
          </button>
        </div>
      </header>

      <div className="opportunity-layout">
        <aside className="scenario-panel" aria-label="Konfigurasi skenario">
          <div className="wizard-progress" aria-label="Tahapan konfigurasi">
            {([1, 2, 3, 4] as SetupStep[]).map((step) => (
              <button
                type="button"
                key={step}
                data-active={setupStep === step}
                aria-current={setupStep === step ? "step" : undefined}
                onClick={() => setSetupStep(step)}
              >
                <span>{step}</span>
                {step === 1 ? "Wilayah" : step === 2 ? "Penilaian" : step === 3 ? "Periode" : "Bobot"}
              </button>
            ))}
          </div>

          <fieldset hidden={setupStep !== 1}>
            <legend>1. Pilih 2–5 provinsi</legend>
            <div className="selector-list region-selector-list">
              {regions.map((region) => (
                <label key={region.code}>
                  <input
                    type="checkbox"
                    checked={scenario.regionCodes.includes(region.code)}
                    onChange={() => toggleRegion(region.code)}
                    disabled={!scenario.regionCodes.includes(region.code) && scenario.regionCodes.length >= 5}
                  />
                  <span>{region.name}</span>
                </label>
              ))}
            </div>
            <small>{scenario.regionCodes.length}/5 dipilih</small>
          </fieldset>

          <fieldset hidden={setupStep !== 2}>
            <legend>2. Pilih hal yang dinilai</legend>
            <div className="selector-list">
              {indicators.map((indicator) => (
                <label key={indicator.code}>
                  <input
                    type="checkbox"
                    checked={scenario.weights.some((item) => item.code === indicator.code)}
                    onChange={() => toggleIndicator(indicator.code)}
                    disabled={!scenario.weights.some((item) => item.code === indicator.code) && scenario.weights.length >= 6}
                  />
                  <span>
                    {indicator.name}
                    <em data-health={indicator.quality_status}>{qualityLabel(indicator.quality_status)}</em>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset hidden={setupStep !== 3}>
            <legend>3. Periode dan cara penilaian</legend>
            <label className="field-label">
              Tahun perbandingan
              <select
                value={activeYear}
                onChange={(event) =>
                  setScenario((current) => ({ ...current, year: Number(event.target.value) }))
                }
              >
                {years.map((year) => (
                  <option value={year} key={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Cara menyetarakan nilai
              <select
                value={scenario.normalization}
                onChange={(event) =>
                  setScenario((current) => ({
                    ...current,
                    normalization: event.target.value as Normalization,
                  }))
                }
              >
                <option value="min_max">Rentang nilai terendah–tertinggi</option>
                <option value="percentile">Posisi relatif antarwilayah</option>
              </select>
            </label>
          </fieldset>

          <fieldset hidden={setupStep !== 4}>
            <legend>4. Bobot dan arah</legend>
            <div className="weight-list">
              {scenario.weights.map((item) => {
                const indicator = indicators.find((candidate) => candidate.code === item.code);
                return (
                  <div className="weight-row" key={item.code}>
                    <strong>{indicator?.name ?? item.code}</strong>
                    <label>
                      Bobot (%)
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={item.weight}
                        onChange={(event) =>
                          setScenario((current) => ({
                            ...current,
                            weights: current.weights.map((weight) =>
                              weight.code === item.code
                                ? { ...weight, weight: Number(event.target.value) }
                                : weight,
                            ),
                          }))
                        }
                      />
                    </label>
                    <label>
                      Hasil yang dianggap lebih baik
                      <select
                        value={item.direction}
                        onChange={(event) =>
                          setScenario((current) => ({
                            ...current,
                            weights: current.weights.map((weight) =>
                              weight.code === item.code
                                ? { ...weight, direction: event.target.value as Direction }
                                : weight,
                            ),
                          }))
                        }
                      >
                        <option value="higher">Lebih tinggi</option>
                        <option value="lower">Lebih rendah</option>
                      </select>
                    </label>
                    <label className="weight-live-slider">
                      <span className="sr-only">Atur cepat bobot {indicator?.name ?? item.code}</span>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="1"
                        value={item.weight}
                        onChange={(event) =>
                          setScenario((current) => ({
                            ...current,
                            weights: rebalanceWeights(current.weights, item.code, Number(event.target.value)),
                          }))
                        }
                      />
                    </label>
                  </div>
                );
              })}
            </div>
            <p className={Math.abs(weightTotal - 100) <= 0.01 ? "weight-valid" : "weight-invalid"}>
              Total bobot: {formatNumber(weightTotal)}%
            </p>
            <label className="field-label">
              Kelengkapan data minimum ({Math.round(scenario.coverageThreshold * 100)}%)
              <input
                type="range"
                min="0.5"
                max="1"
                step="0.05"
                value={scenario.coverageThreshold}
                onChange={(event) =>
                  setScenario((current) => ({
                    ...current,
                    coverageThreshold: Number(event.target.value),
                  }))
                }
              />
            </label>
            <label className="field-label">
              Besar perubahan untuk uji ketahanan ({Math.round(scenario.perturbation * 100)}%)
              <input
                type="range"
                min="0.05"
                max="0.3"
                step="0.05"
                value={scenario.perturbation}
                onChange={(event) =>
                  setScenario((current) => ({
                    ...current,
                    perturbation: Number(event.target.value),
                  }))
                }
              />
            </label>
          </fieldset>

          <div className="wizard-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={setupStep === 1}
              onClick={() => setSetupStep((setupStep - 1) as SetupStep)}
            >
              Kembali
            </button>
            {setupStep < 4 && (
              <button
                type="button"
                className="secondary-button"
                onClick={() => setSetupStep((setupStep + 1) as SetupStep)}
              >
                Lanjut
              </button>
            )}
            <button
              type="button"
              className="primary-button"
              onClick={() => void runAnalysis()}
              disabled={!configurationValid || running}
            >
              {running ? "Menghitung…" : "Hitung skenario"}
            </button>
          </div>
          {!configurationValid && (
            <p className="form-warning">Pilih 2–5 provinsi, periode valid, dan total bobot 100%.</p>
          )}
        </aside>

        <div className="opportunity-results" aria-live="polite">
          {running && <div className="analysis-progress" role="status"><i /><span>Menyusun peringkat dan perbandingan wilayah…</span></div>}
          {score && (
            <div className="live-preview-status" data-active={previewing} role="status">
              <i aria-hidden="true" />
              <span>{previewing ? "Memperbarui peringkat dari bobot terbaru…" : livePreview ? "Peringkat telah menyesuaikan pilihan terbaru" : "Geser bobot untuk melihat perubahan peringkat secara langsung"}</span>
            </div>
          )}
          {!score || !comparison || !sensitivity ? (
            <EmptyState
              eyebrow="Belum ada hasil"
              title="Bangun skenario pertama Anda"
              description="Ikuti empat tahap singkat. Hasil akan menampilkan peringkat, perbandingan, tren, dan ketahanannya."
            />
          ) : (
            <>
              <WorkspaceTabs
                label="Hasil Opportunity Engine"
                active={resultTab}
                onChange={setResultTab}
                tabs={[
                  { id: "ranking", label: "Peringkat", count: score.results.length },
                  { id: "comparison", label: "Perbandingan", count: scenario.weights.length },
                  { id: "trend", label: "Tren", count: comparison.trends.length },
                  { id: "sensitivity", label: "Ketahanan hasil", count: sensitivity.scenario_count },
                  { id: "methodology", label: "Tentang hasil" },
                ]}
              />
              <section className="ranking-panel" aria-labelledby="ranking-title" hidden={resultTab !== "ranking"}>
                <div className="result-heading">
                  <div>
                    <p className="kicker">Peringkat pilihan Anda</p>
                    <h3 id="ranking-title">Lihat wilayah terbaik dan alasannya.</h3>
                  </div>
                  <span>{activeYear}</span>
                </div>
                <div className="ranking-grid">
                  {score.results.map((row, index) => (
                    <article
                      className="ranking-card"
                      key={`${row.region_code}-${row.rank}-${row.score}`}
                      data-eligible={row.eligible}
                      data-tilt
                      style={{
                        "--rank-order": index,
                        "--rank-fill": `${Math.max(0, Math.min(100, row.score ?? 0))}%`,
                      } as CSSProperties}
                    >
                      <span className="rank-mark">{row.rank ? `#${row.rank}` : "Tidak diranking"}</span>
                      <h4>{row.region_name}</h4>
                      <strong>{row.score === null ? "—" : formatNumber(row.score)}</strong>
                      <small>Kelengkapan data {Math.round(row.coverage * 100)}%</small>
                      <span className="rank-meter" aria-hidden="true"><i /></span>
                    </article>
                  ))}
                </div>
                <div className="table-scroll">
                  <table className="responsive-table">
                    <caption>Rincian pembentuk nilai setiap wilayah</caption>
                    <thead>
                      <tr>
                        <th>Wilayah</th>
                        <th>Indikator</th>
                        <th>Nilai asli</th>
                        <th>Skor banding</th>
                        <th>Bobot terpakai</th>
                        <th>Sumbangan nilai</th>
                      </tr>
                    </thead>
                    <tbody>
                      {score.results.flatMap((row) =>
                        row.contributions.map((item) => (
                          <tr key={`${row.region_code}-${item.indicator_code}`}>
                            <td data-label="Wilayah">{row.region_name}</td>
                            <td data-label="Indikator">{indicators.find((indicator) => indicator.code === item.indicator_code)?.name ?? item.indicator_code}</td>
                            <td data-label="Nilai asli">{formatNumber(item.raw_value)}</td>
                            <td data-label="Skor banding">{formatNumber(item.normalized_value, 4)}</td>
                            <td data-label="Bobot terpakai">{item.effective_weight === null ? "—" : `${formatNumber(item.effective_weight)}%`}</td>
                            <td data-label="Sumbangan nilai">{formatNumber(item.contribution, 4)}</td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="comparison-panel" aria-labelledby="comparison-title" hidden={resultTab !== "comparison"}>
                <div className="result-heading">
                  <div>
                    <p className="kicker">Perbandingan indikator</p>
                    <h3 id="comparison-title">Nilai wilayah pada periode yang sama.</h3>
                  </div>
                  <span>{scenario.normalization === "min_max" ? "Min–max" : "Percentile rank"}</span>
                </div>
                {scenario.weights.map((weight) => {
                  const indicator = indicators.find((item) => item.code === weight.code);
                  const summary = comparison.distributions[weight.code];
                  return (
                    <article className="distribution-card" key={weight.code}>
                      <div>
                        <h4>{indicator?.name ?? weight.code}</h4>
                        <p>{indicator?.unit} · nilai {weight.direction === "higher" ? "lebih tinggi" : "lebih rendah"} dianggap lebih baik</p>
                      </div>
                      <div className="distribution-summary">
                        <span>Min {formatNumber(summary?.minimum ?? null)}</span>
                        <span>Median {formatNumber(summary?.median ?? null)}</span>
                        <span>Maks {formatNumber(summary?.maximum ?? null)}</span>
                      </div>
                      <div className="distribution-bars" role="img" aria-label={`Grafik perbandingan ${indicator?.name}`}>
                        {comparison.regions.map((region) => {
                          const value = region.values.find((item) => item.indicator_code === weight.code);
                          return (
                            <div key={region.region_code}>
                              <span>{region.region_name}</span>
                              <i style={{ width: `${Math.max(0, (value?.normalized_value ?? 0) * 100)}%` }} />
                              <b>{formatNumber(value?.raw_value ?? null)}</b>
                            </div>
                          );
                        })}
                      </div>
                    </article>
                  );
                })}
                <div className="table-scroll">
                  <table>
                    <caption>Alternatif data tabel untuk distribusi</caption>
                    <thead><tr><th>Wilayah</th><th>Indikator</th><th>Periode</th><th>Nilai</th><th>Skor banding</th><th>Unit</th></tr></thead>
                    <tbody>
                      {comparison.regions.flatMap((region) =>
                        region.values.map((item) => (
                          <tr key={`${region.region_code}-${item.indicator_code}`}>
                            <td>{region.region_name}</td><td>{item.indicator_code}</td><td>{item.reference_period}</td>
                            <td>{formatNumber(item.raw_value)}</td><td>{formatNumber(item.normalized_value, 4)}</td><td>{item.unit}</td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="trend-panel" aria-labelledby="trend-title" hidden={resultTab !== "trend"}>
                <div className="result-heading"><div><p className="kicker">Perubahan dari waktu ke waktu</p><h3 id="trend-title">Lihat arah perkembangan setiap wilayah.</h3></div></div>
                <div className="table-scroll">
                  <table>
                    <caption>Tren historis untuk wilayah terpilih</caption>
                    <thead><tr><th>Indikator</th><th>Wilayah</th><th>Periode</th><th>Nilai</th><th>Unit</th></tr></thead>
                    <tbody>{comparison.trends.map((row) => <tr key={`${row.indicator_code}-${row.region_code}-${row.period}`}><td>{row.indicator_code}</td><td>{row.region_name}</td><td>{row.period}</td><td>{formatNumber(row.value)}</td><td>{row.unit}</td></tr>)}</tbody>
                  </table>
                </div>
              </section>

              <section className="sensitivity-panel" aria-labelledby="sensitivity-title" hidden={resultTab !== "sensitivity"}>
                <div className="result-heading"><div><p className="kicker">Ketahanan hasil</p><h3 id="sensitivity-title">Apakah peringkat tetap stabil saat prioritas berubah?</h3></div><span>{sensitivity.scenario_count} percobaan</span></div>
                <div className="stability-grid">
                  {sensitivity.stability.map((row) => <article key={row.region_code}><h4>{row.region_name}</h4><strong>{formatNumber(row.unchanged_percent, 0)}%</strong><span>peringkat tetap</span><small>Rentang #{row.min_rank ?? "—"}–#{row.max_rank ?? "—"} · pergeseran maks {row.max_absolute_shift ?? "—"}</small></article>)}
                </div>
                <p className="method-warning">Hasil ini menunjukkan seberapa mudah peringkat berubah ketika prioritas Anda sedikit digeser. Gunakan sebagai bahan pertimbangan, bukan kepastian.</p>
              </section>

              <details className="methodology-drawer" open hidden={resultTab !== "methodology"}>
                <summary>Cara membaca hasil dan sumber data</summary>
                <p>Nilai akhir menggabungkan hasil perbandingan tiap indikator sesuai bobot pilihan Anda. Wilayah dengan data yang tidak cukup tidak dimasukkan ke peringkat.</p>
                <ul>
                  {scenario.weights.map((weight) => {
                    const indicator = indicators.find((item) => item.code === weight.code);
                    return <li key={weight.code}><strong>{indicator?.name}</strong> — {indicator?.definition} <a href={indicator?.source_url} target="_blank" rel="noreferrer">Lihat sumber resmi</a></li>;
                  })}
                </ul>
              </details>
            </>
          )}
        </div>
      </div>
      <WorkspaceToast message={message} tone={message?.toLowerCase().includes("gagal") ? "error" : "success"} onDismiss={() => setMessage(null)} />
    </section>
  );
}
