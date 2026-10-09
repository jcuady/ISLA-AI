import { useCallback, useEffect, useState } from "react";
import { api, type LedgerEntry } from "../lib/api";

interface AuditPayload {
  entries: LedgerEntry[];
  verification: { valid: boolean; entries: number; broken_at?: number; head?: string };
  stats: { total: number; by_event: Record<string, number>; note: string };
}

export default function Ledger() {
  const [data, setData] = useState<AuditPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.audit(60));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 10000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="card">
      <h2>Tamper-evident audit ledger</h2>
      <p className="hint">
        Every inference, redaction and answer appends a SHA-256 hash-chained record. The chain
        stores hashes and metadata only — never raw customer data — so the evidence trail is
        provable to an NPC or BSP examiner without disclosing a single customer record.
      </p>

      {error && <div className="err">{error}</div>}

      {data && (
        <>
          <div className="stats" style={{ marginBottom: 14 }}>
            <div className="stat">
              <div className="k">Chain</div>
              <div className={`v ${data.verification.valid ? "good" : "warn"}`}>
                {data.verification.valid ? "VALID" : `BROKEN @ ${data.verification.broken_at}`}
              </div>
            </div>
            <div className="stat">
              <div className="k">Entries</div>
              <div className="v">{data.verification.entries}</div>
            </div>
            <div className="stat">
              <div className="k">Raw PII stored</div>
              <div className="v good">NONE</div>
            </div>
          </div>

          <div className="muted" style={{ marginBottom: 10 }}>
            {data.stats.note}
          </div>

          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Time (UTC)</th>
                <th>Event</th>
                <th>Metadata</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {data.entries.map((e) => (
                <tr key={e.seq}>
                  <td className="mono">{e.seq}</td>
                  <td className="mono muted">{e.ts.replace("T", " ").replace("+00:00", "")}</td>
                  <td className="mono">{e.event}</td>
                  <td className="mono muted">
                    {Object.entries(e.summary)
                      .map(([k, v]) => `${k}=${v}`)
                      .join("  ")}
                  </td>
                  <td className="mono muted">{e.entry_hash.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}