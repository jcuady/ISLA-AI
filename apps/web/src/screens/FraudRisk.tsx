import * as React from "react";
import { AlertTriangle, BookOpen, ShieldAlert, TriangleAlert, User, Building2 } from "lucide-react";
import { api, type RiskAssessment, type RiskFlag, type RiskIndicator } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";

/**
 * Transaction risk screening.
 *
 * The screen shows what the deterministic engine actually produced: the tier,
 * who is exposed, the words that tripped each indicator, and the action
 * required. Two things it deliberately does NOT do:
 *
 *  - it never renders a gap hook as if it were a citation. Where the governing
 *    rule sits with BSP, SEC, the AMLC or the PCI SSC, the row says so;
 *  - it never shows a clean result as an all-clear. "No red-flag matched" is
 *    not the same claim as "this is safe", and a compliance tool that implies
 *    the second gets trusted for the wrong thing.
 */

const TIER_TONE: Record<string, "safe" | "caution" | "block" | "neutral"> = {
  none: "safe",
  low: "caution",
  medium: "caution",
  high: "block",
  critical: "block",
};

const STARTERS = [
  "A student account received 480,000 in cash deposits from three different people over two days, and sent most of it by wire to a beneficiary abroad the same day.",
  "A caller claiming to be from the bank asked the customer to read the CVV and a one-time password over the phone.",
  "An email from an unknown address asked us to change the beneficiary bank details for the supplier's payroll.",
];

export default function FraudRisk() {
  const [text, setText] = React.useState(STARTERS[0]);
  const [result, setResult] = React.useState<RiskAssessment | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [catalogue, setCatalogue] = React.useState<RiskIndicator[]>([]);
  const [catalogueCount, setCatalogueCount] = React.useState(0);

  React.useEffect(() => {
    api
      .indicators()
      .then((r) => {
        setCatalogue(r.indicators);
        setCatalogueCount(r.count);
      })
      .catch(() => {
        /* the catalogue is context; the screen still works without it */
      });
  }, []);

  async function run() {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      setResult(await api.assess(text));
    } catch (e) {
      // Never leave a stale "clean" verdict on screen after a failure: a
      // compliance officer must not read a failed call as a passed screen.
      setResult(null);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const flags = result?.red_flags ?? [];
  const exposed = result?.exposed ?? [];

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
      <header className="mb-5">
        <h2 className="font-display text-lg font-semibold tracking-tight">
          Screen a transaction or scenario
        </h2>
        <p className="mt-1 text-[12.5px] leading-relaxed text-white/55">
          {catalogueCount > 0
            ? `${catalogueCount} red-flag typologies, matched locally and deterministically.`
            : "Red-flag typologies, matched locally and deterministically."}{" "}
          Nothing is sent anywhere and nothing is scored by a model.
        </p>
      </header>

      <label htmlFor="risk-scenario" className="sr-only">
        Describe the transaction or scenario
      </label>
      <textarea
        id="risk-scenario"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        placeholder="Describe the transaction, the account behaviour, or what the customer told you."
        className="w-full resize-y rounded-lg border border-white/10 bg-abyss-900/60 p-3 text-[13px] leading-relaxed text-white/90 outline-none placeholder:text-white/25 focus:border-lagoon-400/60"
      />

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button onClick={run} disabled={busy || !text.trim()}>
          {busy ? "Screening…" : "Screen scenario"}
        </Button>
        {STARTERS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setText(s)}
            className="rounded-full border border-white/10 px-3 py-1 text-[11.5px] text-white/50 transition-colors hover:border-lagoon-400/40 hover:text-white/80"
          >
            {s.length > 46 ? `${s.slice(0, 46)}…` : s}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="mt-4 flex items-start gap-2 rounded-lg border border-block-500/40 bg-block-500/10 p-3">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-block-400" aria-hidden="true" />
          <p className="text-[12.5px] text-white/80">
            Screening failed: {error}. No verdict was produced, so treat this as
            unscreened rather than clear.
          </p>
        </div>
      )}

      {result && (
        <section className="mt-6 space-y-5">
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <StatusBadge
              tone={TIER_TONE[result.tier] ?? "neutral"}
              label={`${result.tier.toUpperCase()} risk`}
              icon={
                result.tier === "critical" || result.tier === "high" ? (
                  <ShieldAlert className="size-3.5" aria-hidden="true" />
                ) : (
                  <BookOpen className="size-3.5" aria-hidden="true" />
                )
              }
            />
            <div className="flex items-center gap-2 text-[12px] text-white/60">
              <span className="text-white/40">Exposed:</span>
              {exposed.length === 0 && <span className="text-white/50">nobody flagged</span>}
              {exposed.includes("customer") && (
                <span className="inline-flex items-center gap-1 rounded border border-white/12 px-2 py-0.5">
                  <User className="size-3" aria-hidden="true" /> customer
                </span>
              )}
              {exposed.includes("bank") && (
                <span className="inline-flex items-center gap-1 rounded border border-white/12 px-2 py-0.5">
                  <Building2 className="size-3" aria-hidden="true" /> bank
                </span>
              )}
            </div>
            <span className="ml-auto text-[11px] text-white/35">
              {flags.length} indicator{flags.length === 1 ? "" : "s"} ·{" "}
              {result.citation_count} cited · {result.latency_ms} ms
            </span>
          </div>

          <p className="text-[13px] leading-relaxed text-white/75">{result.summary}</p>

          {flags.length === 0 && (
            <p className="rounded-lg border border-white/10 bg-white/[0.02] p-3 text-[12.5px] text-white/60">
              No red-flag indicator matched this scenario. That is the absence of
              a known pattern in the description you gave — it is not a positive
              clearance, and it is not a substitute for the controls that are not
              represented in this catalogue.
            </p>
          )}

          <ul className="space-y-3">
            {flags.map((flag) => (
              <FlagCard key={flag.id} flag={flag} />
            ))}
          </ul>

          {result.required_actions.length > 0 && (
            <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
              <h3 className="font-display text-[13px] font-semibold tracking-tight">
                Required actions
              </h3>
              <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-[12.5px] leading-relaxed text-white/70">
                {result.required_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ol>
            </div>
          )}

          <GapPanel gap={result.coverage_gap} />

          <p className="text-[11px] leading-relaxed text-white/35">{result.footer}</p>
        </section>
      )}
    </div>
  );
}

function FlagCard({ flag }: { flag: RiskFlag }) {
  const hook = flag.legal_hook;
  return (
    <li className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge size="sm" tone={TIER_TONE[flag.tier] ?? "neutral"} label={flag.tier} />
        <h3 className="text-[13px] font-medium text-white/90">{flag.label}</h3>
        {flag.regulator && (
          <span className="text-[11px] text-white/35">· {flag.regulator}</span>
        )}
      </div>

      <p className="mt-2 font-mono text-[11.5px] leading-relaxed text-lagoon-300/90">
        “{flag.evidence}”
      </p>
      <p className="mt-2 text-[12.5px] leading-relaxed text-white/65">{flag.why}</p>
      <p className="mt-2 text-[12.5px] leading-relaxed text-white/85">
        <span className="text-white/40">Do: </span>
        {flag.action}
      </p>

      <div className="mt-3 border-t border-white/8 pt-3">
        {hook.is_gap ? (
          <p className="flex items-start gap-2 text-[11.5px] leading-relaxed text-white/45">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span>
              Governing rule: <span className="text-white/70">{hook.anchor}</span>.{" "}
              Not in corpus — not quoted, not cited. {hook.note}
            </span>
          </p>
        ) : flag.citation ? (
          <div>
            <p className="text-[11px] text-white/35">
              {hook.doc_id} · {flag.citation.label}
              {!flag.citation.anchor_in_text && (
                <span className="text-caution-400">
                  {" "}
                  · approximate match, the anchor phrase is not in this span
                </span>
              )}
            </p>
            <p className="mt-1 text-[12px] leading-relaxed text-white/70">
              {flag.citation.excerpt ?? flag.citation.text}
            </p>
          </div>
        ) : (
          <p className="text-[11.5px] text-white/40">
            {hook.doc_id} · {hook.anchor} — the corpus could not resolve this span
            just now, so it is shown uncited rather than paraphrased.
          </p>
        )}
      </div>
    </li>
  );
}

/** The gap is part of the answer, so it is rendered as a panel, not a footnote. */
function GapPanel({ gap }: { gap: string[] }) {
  if (gap.length === 0) return null;
  return (
    <aside className="rounded-lg border border-caution-500/25 bg-caution-500/[0.06] p-4">
      <h3 className="font-display text-[12.5px] font-semibold tracking-tight text-white/85">
        Not covered by this build
      </h3>
      <ul className="mt-2 space-y-1.5">
        {gap.map((g) => (
          <li key={g} className="text-[11.5px] leading-relaxed text-white/55">
            {g}
          </li>
        ))}
      </ul>
    </aside>
  );
}

export const FRAUD_RISK_VIEW = "risk" as const;