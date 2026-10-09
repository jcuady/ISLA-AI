import * as React from "react";
import { RefreshCw, Link2, ShieldOff, Database, Fingerprint } from "lucide-react";
import { api, type LedgerEntry } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type Audit = Awaited<ReturnType<typeof api.audit>>;

export default function Ledger() {
  const [data, setData] = React.useState<Audit | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setData(await api.audit(50));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const valid = data?.verification.valid ?? false;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      {/* headline proof */}
      <div
        className={cn(
          "flex flex-col gap-4 rounded-panel border p-5 sm:flex-row sm:items-center",
          valid ? "border-semantic-safe/45 bg-semantic-safe/[0.07]" : "border-semantic-block/60 bg-semantic-block/[0.10]",
        )}
      >
        <span
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-xl border",
            valid
              ? "border-semantic-safe/45 bg-semantic-safe/12"
              : "border-semantic-block/55 bg-semantic-block/15",
          )}
          aria-hidden="true"
        >
          {valid ? (
            <Link2 className="size-5 text-semantic-safe" />
          ) : (
            <ShieldOff className="size-5 text-semantic-block" />
          )}
        </span>

        <div className="min-w-0 flex-1">
          <StatusBadge
            tone={valid ? "safe" : "block"}
            label={valid ? "Chain verified" : "Chain broken"}
          />
          <p className="mt-2 text-[13px] leading-relaxed text-white/55">
            {valid
              ? `${data?.verification.entries ?? 0} entries, each SHA-256 linked to the last. ` +
                `Alter one and every entry after it fails verification.`
              : `Verification failed${
                  data?.verification.broken_at ? ` at entry ${data.verification.broken_at}` : ""
                }. Treat this ledger as untrustworthy until resolved.`}
          </p>
        </div>

        <Button variant="secondary" onClick={() => void load()} disabled={busy}>
          <RefreshCw className={cn("size-3.5", busy && "animate-spin")} aria-hidden="true" />
          {busy ? "Verifying" : "Re-verify"}
        </Button>
      </div>

      {/* what it does and does not store */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Database className="mt-0.5 size-4 shrink-0 text-semantic-safe" aria-hidden="true" />
              <div>
                <p className="text-[13px] font-medium text-white/85">Counts and verdicts</p>
                <p className="mt-1 text-[12px] leading-relaxed text-white/45">
                  Entity counts, verdict, latency, hashes. This is what lets you prove what your
                  controls did without disclosing a customer record.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <ShieldOff className="mt-0.5 size-4 shrink-0 text-brand-400" aria-hidden="true" />
              <div>
                <p className="text-[13px] font-medium text-white/85">Never customer text</p>
                <p className="mt-1 text-[12px] leading-relaxed text-white/45">
                  No message body is ever written to disk. Answering &ldquo;what did you collect on
                  the fifteenth?&rdquo; does not itself become a breach.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {error && (
        <div className="mt-4">
          <StatusBadge tone="block" label="Ledger unavailable" />
          <p className="mt-1.5 text-[12px] text-white/50">{error}</p>
        </div>
      )}

      {/* entries */}
      <div className="mt-6 overflow-hidden rounded-panel border border-white/8">
        <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
          <h3 className="font-display text-[11px] font-semibold uppercase tracking-[0.16em] text-white/45">
            Recent entries
          </h3>
          {data && (
            <span className="font-mono text-[11px] text-white/35">
              showing {data.entries.length} of {data.stats.total}
            </span>
          )}
        </div>

        {!data && !error ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : (
          <ul className="divide-y divide-white/5">
            {(data?.entries ?? []).map((e: LedgerEntry) => (
              <li
                key={e.seq}
                className="grid grid-cols-[auto_1fr] items-center gap-3 px-4 py-2.5 transition-colors hover:bg-white/[0.02] sm:grid-cols-[3.5rem_9rem_1fr_auto]"
              >
                <span className="font-mono text-[11px] text-white/25">#{e.seq}</span>
                <span className="font-mono text-[11px] text-white/40">
                  {new Date(e.ts).toLocaleTimeString()}
                </span>
                <span className="truncate text-[12.5px] text-white/75">{e.event}</span>
                <span
                  className="flex items-center gap-1.5 font-mono text-[10.5px] text-white/25"
                  title={`prev ${e.prev_hash.slice(0, 16)}… → ${e.entry_hash.slice(0, 16)}…`}
                >
                  <Fingerprint className="size-3" aria-hidden="true" />
                  {e.entry_hash.slice(0, 10)}
                </span>
              </li>
            ))}
            {!data?.entries.length && (
              <li className="px-4 py-8 text-center text-[13px] text-white/35">No entries yet.</li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}