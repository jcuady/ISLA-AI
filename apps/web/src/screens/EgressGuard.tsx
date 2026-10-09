import { useEffect, useState } from "react";
import { api, type Health, type ScanResult } from "../lib/api";

const SAMPLES: Array<{ label: string; text: string }> = [
  {
    label: "Collections email (high risk)",
    text: `From: Collections Team <collections@usapalmabank.com.ph>
Subject: Urgent - overdue notice for DELOS SANTOS, Maria Concepcion

Magandang araw po,

Nag-apply po ng overdue notice si Maria Concepcion de los Santos.
SSS 12-345-6789, TIN 456-789-012.
Registered mobile 0917 123 4567, GCash number +639171234568.
Credit card ending 4539578763621486, CVV 123, exp 09/28.
Account number: 0056-12345678. Monthly salary PHP 42,500.
Remittance via Cebuana Lhuillier ref #CEB-88213-4455.

Pakisuri na po bago mag-escalate. Salamat!`,
  },
  {
    label: "Structured payment note (redact)",
    text: `Customer reached out about a failed transaction.
Mobile 0917 123 4567, card 4539578763621486 exp 09/28.
Please verify before processing the refund.`,
  },
  {
    label: "Ordinary operations text (safe)",
    text: `Please process invoice INV-2024-00123456 for batch 20240315.
Order reference 9988776655443. Terminal ID 12-34567.
Jealousy ng customer ay malaking bagay, ayon sa Santos (2024).`,
  },
];

function highlight(text: string, result: ScanResult | null) {
  if (!result || result.entities.length === 0) return text;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const e of result.entities) {
    if (e.start < cursor || e.end > text.length) continue;
    parts.push(text.slice(cursor, e.start));
    parts.push(
      <mark key={`${e.start}-${e.type}`} title={`${e.type} · score ${e.score.toFixed(2)}`}>
        {text.slice(e.start, e.end)}
      </mark>
    );
    cursor = e.end;
  }
  parts.push(text.slice(cursor));
  return parts;
}

function maskTokens(text: string) {
  const parts = text.split(/(\[[A-Z]{2,10}-[0-9A-F]{4,}\])/g);
  return parts.map((p, i) =>
    /^\[[A-Z]{2,10}-[0-9A-F]{4,}\]$/.test(p) ? (
      <span key={i} className="token">
        {p}
      </span>
    ) : (
      p
    )
  );
}

export default function EgressGuardScreen({ health }: { health: Health | null }) {
  const [text, setText] = useState(SAMPLES[0].text);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api
      .sample()
      .then((s) => setText((t) => (t.trim() ? t : s.sample)))
      .catch(() => undefined);
  }, []);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.redact(text));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  const verdictClass = result
    ? result.verdict === "SAFE_TO_SEND"
      ? "safe"
      : result.verdict === "REDACT_THEN_SEND"
        ? "redact"
        : "block"
    : "";

  /**
   * Status is never signalled by hue alone. The brand accent is now crimson,
   * so "BLOCK" would be ambiguous without a second channel: every verdict
   * carries a distinct glyph and a written label as well as its colour
   * (WCAG 1.4.1, use of colour).
   */
  const VERDICT_ICON: Record<string, React.ReactNode> = {
    safe: (
      <path
        d="M20 6L9 17l-5-5"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
    redact: (
      <>
        <path d="M12 9v4" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M12 17h.01" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="12" cy="12" r="9" strokeWidth="2" />
      </>
    ),
    block: (
      <>
        <circle cx="12" cy="12" r="9" strokeWidth="2.5" />
        <path d="M5.6 5.6l12.8 12.8" strokeWidth="2.5" strokeLinecap="round" />
      </>
    ),
  };

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Egress Guard</h2>
        <p className="hint">
          Paste or type anything a staff member might send to an external AI. Detection,
          redaction, then a verification pass over the redacted output — all on this machine.
        </p>

        <div className="chips">
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              className="chip"
              onClick={() => {
                setText(s.text);
                setResult(null);
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        <textarea
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste a bank email, a collections ticket, a remittance slip…"
          spellCheck={false}
        />

        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn" onClick={() => void run()} disabled={busy || !text.trim()}>
            {busy ? "Scanning…" : "Scan & redact"}
          </button>
          <button className="btn ghost" onClick={() => { setText(""); setResult(null); }}>
            Clear
          </button>
          {health?.models?.ner && !health.models.ner.available && (
            <span className="muted">
              GLiNER NER not loaded — regex + Luhn ensemble still active
            </span>
          )}
        </div>

        {error && <div className="err">{error}</div>}
      </div>

      {result && (
        <div className="card">
          <div className={`verdict ${verdictClass}`}>
            <svg
              className="vicon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              aria-hidden="true"
            >
              {VERDICT_ICON[verdictClass]}
            </svg>
            <span className="vlabel">{result.verdict_label}</span>
            <span className="muted">{result.notes.join(" ")}</span>
            <span className="vmeta">
              {result.latency_ms.toFixed(0)} ms · {result.passes} pass
              {result.passes > 1 ? "es" : ""}
            </span>
          </div>

          <div className="stats">
            <div className="stat">
              <div className="k">Entities</div>
              <div className="v">{result.entities.length}</div>
            </div>
            <div className="stat">
              <div className="k">Redacted</div>
              <div className="v">{result.redaction_map.length}</div>
            </div>
            <div className="stat">
              <div className="k">Residual leakage</div>
              <div className={`v ${result.residual_leakage === 0 ? "good" : "warn"}`}>
                {(result.residual_leakage * 100).toFixed(2)}%
              </div>
            </div>
            <div className="stat">
              <div className="k">Verification</div>
              <div className={`v ${result.verified_clean ? "good" : "warn"}`}>
                {result.verified_clean ? "CLEAN" : "RESIDUAL"}
              </div>
            </div>
            <div className="stat">
              <div className="k">Latency</div>
              <div className="v">{result.latency_ms.toFixed(0)} ms</div>
            </div>
          </div>

          <div className="diff" style={{ marginTop: 14 }}>
            <div className="pane">
              <span className="label">Original — detected entities highlighted</span>
              {highlight(result.original, result)}
            </div>
            <div className="pane">
              <span className="label">Redacted — HMAC pseudonyms, joins preserved</span>
              {maskTokens(result.redacted)}
            </div>
          </div>

          {Object.keys(result.entity_counts).length > 0 && (
            <table style={{ marginTop: 14 }}>
              <thead>
                <tr>
                  <th>Entity type</th>
                  <th>Count</th>
                  <th>Value (original)</th>
                  <th>Score</th>
                  <th>Stage</th>
                </tr>
              </thead>
              <tbody>
                {result.entities
                  .filter((e) => e.type !== "PERSON")
                  .map((e, i) => (
                    <tr key={`${e.start}-${e.type}-${i}`}>
                      <td className="mono">{e.type}</td>
                      <td className="mono">1</td>
                      <td className="mono">{e.text}</td>
                      <td className="mono">{e.score.toFixed(2)}</td>
                      <td className="muted">{e.reasons.join(", ")}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </>
  );
}