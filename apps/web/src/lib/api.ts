export interface AirgapResult {
  air_gapped: boolean;
  outbound_blocked: boolean;
  resolver_available: boolean;
  bind_host: string;
  checked_at: string;
  elapsed_ms: number;
  note: string;
  probes: Array<{
    target: string;
    label: string;
    reachable?: boolean;
    resolved?: boolean;
    error: string | null;
    elapsed_ms: number;
  }>;
}

export interface Entity {
  type: string;
  start: number;
  end: number;
  text: string;
  score: number;
  stage: string;
  validated: boolean;
  reasons: string[];
}

export interface RedactionMapItem {
  type: string;
  original_length: number;
  replacement: string;
  mode: string;
  score: number;
}

export interface ScanResult {
  original: string;
  redacted: string;
  verdict: "SAFE_TO_SEND" | "REDACT_THEN_SEND" | "BLOCK_ESCALATE";
  verdict_label: string;
  verified_clean: boolean;
  residual_leakage: number;
  passes: number;
  latency_ms: number;
  notes: string[];
  redaction_map: RedactionMapItem[];
  entities: Entity[];
  entity_counts: Record<string, number>;
}

export interface Citation {
  id: string;
  label: string;
  doc_id: string;
  doc_title: string;
  issuer: string;
  section: string;
  effective_date: string;
  url: string;
  doc_type: string;
  rank: number;
  score: number;
}

export interface CopilotAnswer {
  question: string;
  answer: string;
  refused: boolean;
  confidence: number;
  citations: Citation[];
  sources: Array<Record<string, unknown>>;
  footer: string;
  latency_ms: number;
  retrieval_mode: string;
  llm_used: boolean;
  notes: string[];
}

export interface Health {
  status: string;
  product: string;
  /** What the acronym expands to: "In-Situ Local AI". */
  stands_for?: string;
  tagline: string;
  bind: { host: string; port: number; loopback_only: boolean };
  corpus: { chunks: number; documents: number; dense_ready: boolean; total_chars: number } | null;
  models: Record<string, { available: boolean; name: string | null; role: string }>;
  engines: Record<string, boolean>;
}

export interface LedgerEntry {
  seq: number;
  ts: string;
  event: string;
  summary: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    // Enables a real cancel button. Without it, a "Stop" control could only
    // ignore the response, leaving the request running on the server.
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text.slice(0, 300)}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export interface RiskCitation {
  doc_id: string;
  doc_title: string;
  issuer: string;
  section: string;
  url: string;
  doc_type: string;
  label: string;
  text: string;
  /** A window centred on the anchor phrase, so the reader sees the words that
   *  fired the indicator rather than the head of the section. */
  excerpt?: string;
  score: number;
  /** False when the anchor was not present and the span is a near match. */
  anchor_in_text: boolean;
}

export interface RiskLegalHook {
  doc_id: string;
  anchor: string;
  note: string;
  /** True when the governing rule sits with a regulator this build could not
   *  retrieve. Such a hook is never presented as a citation. */
  is_gap: boolean;
}

export interface RiskFlag {
  id: string;
  label: string;
  tier: string;
  exposure: string[];
  evidence: string;
  why: string;
  action: string;
  regulator: string;
  legal_hook: RiskLegalHook;
  citation: RiskCitation | null;
}

export interface RiskAssessment {
  tier: string;
  risk_tier: string;
  exposed: string[];
  red_flags: RiskFlag[];
  required_actions: string[];
  summary: string;
  coverage_gap: string[];
  citation_count: number;
  degraded: boolean;
  footer: string;
  latency_ms: number;
}

export interface RiskIndicator {
  id: string;
  label: string;
  tier: string;
  exposure: string[];
  why: string;
  action: string;
  regulator: string;
  legal_hook: { doc_id: string; anchor: string; note: string; is_gap: boolean };
}

export const api = {
  health: () => get<Health>("/api/health"),
  airgap: () => get<AirgapResult>("/api/airgap"),
  redact: (text: string, signal?: AbortSignal) =>
    post<ScanResult>("/api/pii/redact", { text }, signal),
  scan: (text: string, signal?: AbortSignal) =>
    post<ScanResult>("/api/pii/scan", { text }, signal),
  ask: (text: string, signal?: AbortSignal) =>
    post<CopilotAnswer>("/api/copilot/ask", { text }, signal),
  assess: (text: string, signal?: AbortSignal) =>
    post<RiskAssessment>("/api/risk/assess", { text }, signal),
  indicators: () =>
    get<{ count: number; indicators: RiskIndicator[]; coverage_gap: string[] }>(
      "/api/risk/indicators",
    ),
  audit: (limit = 50) =>
    get<{
      entries: LedgerEntry[];
      verification: { valid: boolean; entries: number; broken_at?: number; head?: string };
      stats: { total: number; by_event: Record<string, number>; note: string };
    }>(`/api/audit?limit=${limit}`),
  sample: () => get<{ sample: string }>("/api/sample"),
};