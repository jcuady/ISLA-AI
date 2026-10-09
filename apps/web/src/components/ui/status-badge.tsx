import * as React from "react";
import { CheckCircle2, AlertCircle, ShieldOff, Sparkles, HelpCircle, CircleDashed } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * The single place KALIX status colour is decided.
 *
 * The brand accent is crimson, so BLOCK can no longer be the only red thing in
 * the product. To keep status unambiguous next to brand chrome, every tone is
 * signalled on FOUR independent channels:
 *
 *   1. hue        a token reserved for this tone
 *   2. form       a filled, bordered pill - never a bare text tint
 *   3. icon       a distinct glyph per tone
 *   4. label      visible text, always present
 *
 * Desaturate or print this in black and white and the tones remain
 * distinguishable. Screen code must use this component rather than hand-rolling
 * a colour, or the guarantee is lost.
 */

export type StatusTone =
  | "safe"
  | "caution"
  | "block"
  | "refuse"
  | "info"
  | "neutral";

const TONE: Record<
  StatusTone,
  { icon: React.ComponentType<{ className?: string }>; className: string }
> = {
  safe: {
    icon: CheckCircle2,
    className: "border-semantic-safe/45 bg-semantic-safe/12 text-semantic-safe",
  },
  caution: {
    icon: AlertCircle,
    className: "border-semantic-caution/45 bg-semantic-caution/12 text-semantic-caution",
  },
  block: {
    // BLOCK is the loudest state in the product: 2px border, heaviest weight.
    icon: ShieldOff,
    className:
      "border-semantic-block/70 bg-semantic-block/18 text-semantic-block font-extrabold tracking-wide",
  },
  refuse: {
    icon: HelpCircle,
    className: "border-semantic-refuse/45 bg-semantic-refuse/12 text-semantic-refuse",
  },
  info: {
    icon: Sparkles,
    className: "border-brand-500/40 bg-brand-500/12 text-brand-300",
  },
  neutral: {
    // A dashed circle reads as "nothing to assert". It must not repeat the
    // HelpCircle glyph used by `refuse`: two tones sharing an icon is exactly
    // the desaturated-collision the four-channel rule exists to prevent.
    icon: CircleDashed,
    className: "border-white/12 bg-white/[0.05] text-white/70",
  },
};

/** Maps an Egress Guard verdict string onto a tone. */
export function verdictTone(verdict: string): StatusTone {
  switch (verdict) {
    case "SAFE_TO_SEND":
      return "safe";
    case "REDACT_THEN_SEND":
      return "caution";
    case "BLOCK_ESCALATE":
      return "block";
    default:
      return "neutral";
  }
}

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone: StatusTone;
  /** Visible label. Required: status is never communicated by colour alone. */
  label: string;
  icon?: React.ReactNode;
  size?: "sm" | "md";
}

export function StatusBadge({
  tone,
  label,
  icon,
  size = "md",
  className,
  ...props
}: StatusBadgeProps) {
  const Icon = TONE[tone].icon;
  return (
    <span
      // `role="status"` announces tone changes to assistive tech without
      // stealing focus mid-answer.
      role="status"
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full border font-mono uppercase",
        size === "md" ? "px-3 py-1 text-[11px] tracking-[0.08em]" : "px-2 py-0.5 text-[10px]",
        TONE[tone].className,
        className,
      )}
      {...props}
    >
      {icon ?? <Icon className="size-3.5 shrink-0" aria-hidden="true" />}
      <span className="truncate">{label}</span>
    </span>
  );
}