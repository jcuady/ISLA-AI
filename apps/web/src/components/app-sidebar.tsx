import * as React from "react";
import {
  ShieldCheck,
  MessageSquareText,
  ScanLine,
  ScrollText,
  Plus,
  Landmark,
  Cpu,
  Wifi,
  WifiOff,
  CircleAlert,
  ExternalLink,
} from "lucide-react";
import { KalixMark } from "@/components/kalix-mark";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";
import type { AirgapResult, Health } from "@/lib/api";

export type ViewId = "copilot" | "egress" | "ledger";

interface NavItem {
  id: ViewId;
  label: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
}

/** Order is deliberate: the two controls a bank officer uses daily come first. */
export const NAV_ITEMS: NavItem[] = [
  {
    id: "copilot",
    label: "DPA Copilot",
    hint: "Ask the law, get citations",
    icon: MessageSquareText,
  },
  {
    id: "egress",
    label: "Egress Guard",
    hint: "Scan before you paste",
    icon: ScanLine,
  },
  {
    id: "ledger",
    label: "Audit Ledger",
    hint: "Hash-chained proof",
    icon: ScrollText,
  },
];

export interface AppSidebarProps {
  active: ViewId;
  onNavigate: (view: ViewId) => void;
  gap: AirgapResult | null;
  gapError: string | null;
  health: Health | null;
  onNewChat: () => void;
  canNewChat: boolean;
  /** Called when a starter prompt is chosen. Hidden on non-chat views. */
  onStarter?: (question: string) => void;
  className?: string;
}

const STARTERS = [
  "Ilang oras dapat ko i-report ang data breach?",
  "Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?",
  "Kailangan ba mag-register ng AI credit scoring model ang banko namin?",
];

export function AppSidebar({
  active,
  onNavigate,
  gap,
  gapError,
  health,
  onNewChat,
  canNewChat,
  onStarter,
  className,
}: AppSidebarProps) {
  const airGapped = gap?.air_gapped ?? false;

  return (
    <aside
      className={cn(
        "flex h-full w-[280px] shrink-0 flex-col border-r border-white/8 bg-noir-900",
        className,
      )}
      aria-label="Primary navigation"
    >
      {/* ---- brand ---- */}
      <div className="flex items-center gap-2.5 px-5 pb-5 pt-5">
        <KalixMark size={26} />
        <div className="min-w-0 flex-1">
          <p className="font-display text-[15px] font-extrabold tracking-[0.14em]">KALIX</p>
          <p className="truncate text-[11px] text-white/40">Walang datos na lumalabas.</p>
        </div>
      </div>

      {/* ---- primary action ---- */}
      <div className="px-4 pb-4">
        <Button
          className="w-full justify-start"
          onClick={onNewChat}
          disabled={!canNewChat}
          title={canNewChat ? "Start a new conversation" : "Switch to the Copilot first"}
        >
          <Plus className="size-4" aria-hidden="true" />
          New conversation
        </Button>
      </div>

      {/* ---- navigation ---- */}
      <nav className="px-3">
        <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
          Controls
        </p>
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.id;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onNavigate(item.id)}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                    isActive
                      ? "bg-brand-500/12 text-white"
                      : "text-white/60 hover:bg-white/[0.05] hover:text-white",
                  )}
                >
                  <span
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-md border transition-colors",
                      isActive
                        ? "border-brand-500/40 bg-brand-500/15 text-brand-300"
                        : "border-white/10 bg-white/[0.03] text-white/50 group-hover:text-white/80",
                    )}
                  >
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{item.label}</span>
                    <span className="block truncate text-[11px] text-white/35">{item.hint}</span>
                  </span>
                  {isActive && (
                    <span
                      className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500"
                      aria-hidden="true"
                    />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ---- starter prompts, chat view only ---- */}
      {active === "copilot" && onStarter && (
        <div className="mt-6 px-3">
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
            Try asking
          </p>
          <ul className="space-y-1">
            {STARTERS.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => onStarter(q)}
                  className="w-full rounded-lg border border-white/8 px-3 py-2 text-left text-[12px] leading-snug text-white/55 transition-colors hover:border-brand-500/35 hover:bg-brand-500/[0.06] hover:text-white"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* pinned to the bottom: the proof, not decoration ---- */}
      <div className="mt-auto space-y-2 border-t border-white/8 p-4">
        {gapError ? (
          <StatusBadge tone="block" label="Probe error" className="w-full justify-start" />
        ) : (
          <StatusBadge
            tone={airGapped ? "safe" : "caution"}
            label={airGapped ? "Network: air-gapped" : "Network: connected"}
            className="w-full justify-start"
          />
        )}

        <dl className="space-y-1.5 text-[11px]">
          <div className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-1.5 text-white/40">
              <Landmark className="size-3" aria-hidden="true" />
              Corpus
            </dt>
            <dd className="font-mono text-white/70">
              {health?.corpus?.documents ?? 0} docs · {health?.corpus?.chunks ?? 0} sections
            </dd>
          </div>
          <div className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-1.5 text-white/40">
              <Cpu className="size-3" aria-hidden="true" />
              Bind
            </dt>
            <dd className="font-mono text-white/70">
              {health?.bind?.loopback_only ? "127.0.0.1 only" : "UNEXPECTED"}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-1.5 text-white/40">
              {airGapped ? (
                <WifiOff className="size-3" aria-hidden="true" />
              ) : (
                <Wifi className="size-3" aria-hidden="true" />
              )}
              Probe
            </dt>
            <dd className="font-mono text-white/70">{gap ? `${gap.elapsed_ms} ms` : "…"}</dd>
          </div>
        </dl>

        <a
          href="/"
          className="flex items-center gap-1.5 pt-1 text-[11px] text-white/35 transition-colors hover:text-white"
        >
          <ExternalLink className="size-3" aria-hidden="true" />
          Product site
        </a>

        <p className="flex items-start gap-1.5 pt-2 text-[10px] leading-relaxed text-white/25">
          <CircleAlert className="mt-px size-3 shrink-0" aria-hidden="true" />
          Not legal advice. Verify every citation before relying on it.
        </p>
      </div>
    </aside>
  );
}

/** Small icon-only header for compact viewports. */
export function ViewIcon({ id, className }: { id: ViewId; className?: string }) {
  const item = NAV_ITEMS.find((n) => n.id === id)!;
  const Icon = item.icon;
  return <Icon className={className} aria-hidden="true" />;
}