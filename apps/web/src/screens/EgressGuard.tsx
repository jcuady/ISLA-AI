import * as React from "react";
import { ScanLine, Eraser, ShieldCheck, ShieldAlert, ShieldX, Layers, Timer, ListChecks } from "lucide-react";
import { api, type ScanResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatusBadge, verdictTone } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

const SAMPLES = [
  {
    label: "Collections email",
    hint: "High risk — will BLOCK",
    kind: "block",
    load: async () => (await api.sample()).sample,
  },
  {
    label: "Payment note",
    hint: "Redact then send",
    kind: "caution",
    load: async () =>
      "Magbayad si Maria ng PHP 42,500 sa account 0056-12345678 sangguniang 2024-03-15. " +
      "Reference INV-2024-00123456, batch 20240315.",
  },
  {
    label: "Operations text",
    hint: "Safe — no PII",
    kind: "safe",
    load: async () =>
      "Please process invoice INV-2024-00123456 for batch 20240315. " +
      "Kindly confirm receipt within five business days.",
  },
] as const;

/** The verdict drives every visual decision below. Never branch on raw colour. */
function verdictIcon(verdict: string) {
  switch (verdictTone(verdict)) {
    case "safe":
      return ShieldCheck;
    case "caution":
      return ShieldAlert;
    default:
      return ShieldX;
  }
}

export default function EgressGuard() {
  const [text, setText] = React.useState("");
  const [result, setResult] = React.useState<ScanResult | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const run = React.useCallback(async (input: string) => {
    if (!input.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.redact(input));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setBusy(false);
    }
  }, []);

  // Load the high-risk sample on mount so the screen is never an empty box.
  React.useEffect(() => {
    let alive = true;
    api
      .sample()
      .then((r) => {
        if (alive) setText(r.sample);
      })
      .catch(() => {
        /* the officer can paste their own text */
      });
    return () => {
      alive = false;
    };
  }, []);

  const tone = result ? verdictTone(result.verdict) : null;
  const VerdictIcon = result ? verdictIcon(result.verdict) : ShieldCheck;

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      <div className="grid gap-4 lg:grid-cols-2">
        {/* ---------- input ---------- */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ScanLine className="size-4 text-brand-400" aria-hidden="true" />
              Text to scan
            </CardTitle>
            <CardDescription>
              Paste anything a staff member might send to an external AI. Detection, redaction and
              a verification pass all run on this machine.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste a collections email, a chat message, a payment note…"
              aria-label="Text to scan for personal information"
              rows={9}
              className="w-full resize-y rounded-lg border border-white/10 bg-noir-950/60 p-3 font-mono text-[12.5px] leading-relaxed text-white/90 placeholder:text-white/25 focus:border-brand-500/60 focus:outline-none"
            />

            <div className="flex flex-wrap gap-1.5">
              {SAMPLES.map((s) => (
                <button
                  key={s.label}
                  type="button"
                  onClick={async () => {
                    const v = await s.load();
                    setText(v);
                    await run(v);
                  }}
                  title={s.hint}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-[11.5px] transition-colors",
                    s.kind === "block" &&
                      "border-semantic-block/40 text-semantic-block/90 hover:bg-semantic-block/12",
                    s.kind === "caution" &&
                      "border-semantic-caution/40 text-semantic-caution/90 hover:bg-semantic-caution/12",
                    s.kind === "safe" &&
                      "border-semantic-safe/40 text-semantic-safe/90 hover:bg-semantic-safe/12",
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>

            <div className="mt-auto flex items-center gap-2 pt-1">
              <Button onClick={() => void run(text)} disabled={busy || !text.trim()} className="flex-1">
                {busy ? "Scanning…" : "Scan & redact"}
              </Button>
              <Button
                variant="secondary"
                size="icon"
                aria-label="Clear"
                title="Clear"
                onClick={() => {
                  setText("");
                  setResult(null);
                  setError(null);
                }}
                disabled={busy}
              >
                <Eraser className="size-4" aria-hidden="true" />
              </Button>
            </div>

            {error && (
              <StatusBadge tone="block" label="Scan failed" className="mt-1" />
            )}
            {error && <p className="text-[12px] leading-relaxed text-white/50">{error}</p>}
          </CardContent>
        </Card>

        {/* ---------- results ---------- */}
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Verdict</CardTitle>
            <CardDescription>
              After redaction the whole detector runs again over KALIX's own output. Anything that
              survives escalates instead of shipping.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-4">
            {!result ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-2 py-12 text-center">
                <ShieldCheck className="size-8 text-white/15" aria-hidden="true" />
                <p className="text-[13px] text-white/35">
                  No scan yet. Load a sample or paste your own text.
                </p>
              </div>
            ) : (
              <>
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-xl border p-4",
                    tone === "safe" && "border-semantic-safe/45 bg-semantic-safe/[0.08]",
                    tone === "caution" && "border-semantic-caution/45 bg-semantic-caution/[0.08]",
                    tone === "block" &&
                      "border-2 border-semantic-block/70 bg-semantic-block/[0.12]",
                  )}
                >
                  <VerdictIcon
                    className={cn(
                      "size-7 shrink-0",
                      tone === "safe" && "text-semantic-safe",
                      tone === "caution" && "text-semantic-caution",
                      tone === "block" && "text-semantic-block",
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <StatusBadge tone={tone!} label={result.verdict_label} />
                    <p className="mt-1.5 text-[12px] leading-relaxed text-white/50">
                      {(result.notes ?? []).join(" ")}
                    </p>
                  </div>
                </div>

                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Metric
                    icon={ShieldCheck}
                    label="Residual"
                    value={`${(result.residual_leakage * 100).toFixed(2)}%`}
                    tone={result.residual_leakage === 0 ? "good" : "warn"}
                  />
                  <Metric icon={Timer} label="Latency" value={`${result.latency_ms.toFixed(0)} ms`} />
                  <Metric
                    icon={ListChecks}
                    label="Passes"
                    value={String(result.passes)}
                    tone={result.passes > 1 ? "good" : undefined}
                  />
                  <Metric
                    icon={Layers}
                    label="Entities"
                    value={String(result.entities.length)}
                  />
                </dl>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Pane label="Original" text={result.original} testId="pane-original" />
                  <Pane label="Redacted" text={result.redacted} testId="pane-redacted" accent />
                </div>

                {!!result.entities.length && (
                  <div>
                    <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
                      Detected ({result.entities.length})
                    </p>
                    <ul className="flex flex-wrap gap-1.5">
                      {result.entities.map((e, i) => (
                        <li
                          key={`${e.type}-${e.start}-${i}`}
                          className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 font-mono text-[11px] text-white/70"
                          title={e.reasons?.join(" · ") || undefined}
                        >
                          <span className="text-brand-300">{e.type}</span>{" "}
                          <span className="text-white/40">{e.text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone?: "good" | "warn";
}) {
  return (
    <div className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
      <dt className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.1em] text-white/40">
        <Icon className="size-3" aria-hidden="true" />
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1 font-mono text-[15px] font-semibold",
          tone === "good" && "text-semantic-safe",
          tone === "warn" && "text-semantic-caution",
          !tone && "text-white",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function Pane({
  label,
  text,
  testId,
  accent,
}: {
  label: string;
  text: string;
  testId: string;
  accent?: boolean;
}) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
        {label}
      </p>
      <div
        data-testid={testId}
        className={cn(
          "max-h-52 overflow-y-auto whitespace-pre-wrap break-words rounded-lg border p-3",
          "font-mono text-[12px] leading-relaxed",
          accent
            ? "border-brand-500/25 bg-brand-500/[0.06] text-white/85"
            : "border-white/10 bg-noir-950/60 text-white/55",
        )}
      >
        {text}
      </div>
    </div>
  );
}