import * as React from "react";
import { Copy, Check, BookOpen, Ban, Clock3, Sparkles } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";
import type { Citation } from "@/lib/api";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  refused?: boolean;
  confidence?: number;
  latencyMs?: number;
  retrievalMode?: string;
  llmUsed?: boolean;
  footer?: string;
  error?: string;
}

/** Full citation text, revealed on demand. Off by default so the thread reads
 *  as a conversation rather than a wall of legal boilerplate. */
function CitationChip({ citation }: { citation: Citation }) {
  const [open, setOpen] = React.useState(false);
  return (
    <span className="inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={cn(
          "group inline-flex max-w-full items-center gap-1.5 rounded-lg border border-semantic-cite/35",
          "bg-semantic-cite/10 px-2 py-1 font-mono text-[11px] text-semantic-cite/90",
          "transition-colors hover:bg-semantic-cite/20",
        )}
      >
        <BookOpen className="size-3 shrink-0" aria-hidden="true" />
        <span className="truncate">{citation.label}</span>
      </button>
      {open && (
        <span className="mt-2 block w-full rounded-lg border border-white/10 bg-abyss-850 p-3 text-[12px] leading-relaxed text-white/65">
          <span className="block font-semibold text-white/85">{citation.doc_title}</span>
          <span className="block text-white/45">
            {citation.issuer} · effective {citation.effective_date}
          </span>
          <span className="mt-1.5 block text-white/55">Section: {citation.section}</span>
          <span className="mt-1.5 block break-all font-mono text-[11px] text-white/35">
            {citation.url}
          </span>
        </span>
      )}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = React.useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access can be denied; the button simply does not confirm.
      setCopied(false);
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-md p-1.5 text-white/35 transition-colors hover:bg-white/8 hover:text-white"
      aria-label={copied ? "Copied" : "Copy answer"}
      title={copied ? "Copied" : "Copy answer"}
    >
      {copied ? (
        <Check className="size-3.5 text-semantic-safe" aria-hidden="true" />
      ) : (
        <Copy className="size-3.5" aria-hidden="true" />
      )}
    </button>
  );
}

export function UserMessage({ message }: { message: ChatMessageData }) {
  return (
    <div className="flex justify-end px-4 py-3 sm:px-6">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand-500/15 px-4 py-2.5 text-[14.5px] leading-relaxed text-white ring-1 ring-brand-500/25 sm:max-w-[75%]">
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
      </div>
    </div>
  );
}

export function AssistantMessage({ message }: { message: ChatMessageData }) {
  if (message.error) {
    return (
      <div className="flex gap-3 px-4 py-4 sm:px-6">
        <span
          className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-semantic-block/40 bg-semantic-block/12"
          aria-hidden="true"
        >
          <Ban className="size-3.5 text-semantic-block" />
        </span>
        <div className="min-w-0 flex-1">
          <StatusBadge tone="block" label="Request failed" />
          <p className="mt-2 text-[13px] leading-relaxed text-white/60">{message.error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 px-4 py-4 sm:px-6">
      <span
        className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-brand-500/35 bg-brand-500/12"
        aria-hidden="true"
      >
        <Sparkles className="size-3.5 text-brand-400" />
      </span>

      <div className="min-w-0 flex-1">
        {message.refused ? (
          <div className="rounded-xl border border-semantic-refuse/35 bg-semantic-refuse/[0.08] p-4">
            <StatusBadge tone="refuse" label="Refused — outside corpus" />
            <p className="mt-3 whitespace-pre-wrap text-[14.5px] leading-relaxed text-white/80">
              {message.content}
            </p>
            <p className="mt-2 text-[12px] leading-relaxed text-white/45">
              No citation was returned, because none could be supported. Correct refusal is the
              behaviour that stops a model inventing a circular number.
            </p>
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-[14.5px] leading-relaxed text-white/90">
            {message.content}
          </p>
        )}

        {!!message.citations?.length && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.citations.map((c) => (
              <CitationChip key={c.id} citation={c} />
            ))}
          </div>
        )}

        <div className="mt-2.5 flex flex-wrap items-center gap-2 text-[11px] text-white/35">
          {typeof message.latencyMs === "number" && (
            <span className="inline-flex items-center gap-1 font-mono">
              <Clock3 className="size-3" aria-hidden="true" />
              {message.latencyMs.toFixed(0)} ms
            </span>
          )}
          {typeof message.confidence === "number" && (
            <span className="font-mono">conf {message.confidence.toFixed(2)}</span>
          )}
          {message.retrievalMode && (
            <span className="font-mono">{message.retrievalMode}</span>
          )}
          {!message.llmUsed && !message.refused && (
            <span
              className="rounded border border-white/10 px-1.5 py-0.5 font-mono"
              title="No generative model loaded - the answer is quoted verbatim from cited spans"
            >
              extractive
            </span>
          )}
          {!message.refused && <CopyButton text={message.content} />}
        </div>

        {message.footer && (
          <p className="mt-2 border-t border-white/8 pt-2 text-[11px] leading-relaxed text-white/30">
            {message.footer}
          </p>
        )}
      </div>
    </div>
  );
}