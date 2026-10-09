import * as React from "react";
import { Landmark, Scale, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { ChatComposer } from "@/components/ui/chat-composer";
import { TypingDots } from "@/components/ui/skeleton";
import { IslaMark } from "@/components/isla-mark";
import {
  AssistantMessage,
  UserMessage,
  type ChatMessageData,
} from "@/components/chat/message";
import { cn } from "@/lib/utils";

/** Questions that exercise the parts of the system worth seeing first. */
const SUGGESTIONS = [
  {
    icon: ShieldAlert,
    title: "Breach reporting clock",
    q: "Ilang oras dapat ko i-report ang data breach?",
  },
  {
    icon: Landmark,
    title: "Outsourcing to a vendor",
    q: "Pwede ba ipasa ang CDR ng customer ko sa vendor namin sa Singapore?",
  },
  {
    icon: Scale,
    title: "Rules for automated decisions",
    q: "Can our call center use AI to score our agents?",
  },
];

let seq = 0;
const nextId = () => `m${Date.now().toString(36)}-${(seq += 1)}`;

export interface CopilotProps {
  /** Bumped by the shell when "New conversation" is pressed. */
  resetKey: number;
  /** Question injected by a sidebar starter click. */
  externalQuestion?: { q: string; nonce: number } | null;
}

export default function Copilot({ resetKey, externalQuestion }: CopilotProps) {
  const [messages, setMessages] = React.useState<ChatMessageData[]>([]);
  const [draft, setDraft] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const abortRef = React.useRef<AbortController | null>(null);

  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const endRef = React.useRef<HTMLDivElement | null>(null);

  // New conversation: clear the thread and release any in-flight request.
  React.useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setDraft("");
    setBusy(false);
  }, [resetKey]);

  // Pin to the newest message as the thread grows.
  React.useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const send = React.useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed) return;

    const userMsg: ChatMessageData = { id: nextId(), role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const answer = await api.ask(trimmed, controller.signal);
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: answer.answer,
          citations: answer.citations,
          refused: answer.refused,
          confidence: answer.confidence,
          latencyMs: answer.latency_ms,
          retrievalMode: answer.retrieval_mode,
          llmUsed: answer.llm_used,
          footer: answer.footer,
        },
      ]);
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: "",
          error: err instanceof Error ? err.message : String(err),
        },
      ]);
    } finally {
      abortRef.current = null;
      setBusy(false);
    }
  }, []);

  // A starter clicked in the sidebar arrives here.
  React.useEffect(() => {
    if (externalQuestion) void send(externalQuestion.q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalQuestion?.nonce]);

  const stop = React.useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
  }, []);

  const empty = messages.length === 0;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
        {empty ? (
          <EmptyState onPick={(q) => void send(q)} />
        ) : (
          <div className="mx-auto w-full max-w-3xl py-4">
            {messages.map((m) =>
              m.role === "user" ? (
                <UserMessage key={m.id} message={m} />
              ) : (
                <AssistantMessage key={m.id} message={m} />
              ),
            )}
            {busy && (
              <div className="flex gap-3 px-4 py-4 sm:px-6">
                <span
                  className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-brand-500/35 bg-brand-500/12"
                  aria-hidden="true"
                >
                  <IslaMark size={14} />
                </span>
                <div className="pt-1">
                  <TypingDots />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Composer pinned to the bottom, like a modern chat surface. */}
      <div className="shrink-0 border-t border-white/8 bg-abyss-950/80 px-4 pb-4 pt-3 backdrop-blur-sm sm:px-6">
        <div className="mx-auto w-full max-w-3xl">
          <ChatComposer
            value={draft}
            onChange={setDraft}
            onSubmit={(q) => void send(q)}
            onStop={stop}
            busy={busy}
            placeholder="Ask about the Data Privacy Act, in Taglish or English…"
            footer={
              <p className="mt-2 text-center text-[11px] leading-relaxed text-white/30">
                Answers are quoted from cited spans in {7} Philippine instruments. Not legal advice.
              </p>
            }
          />
        </div>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div
      className={cn(
        "flex h-full flex-col items-center justify-center px-6 py-12 text-center",
      )}
    >
      <span
        className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-brand-500/30 bg-brand-500/10"
        aria-hidden="true"
      >
        <IslaMark size={28} />
      </span>
      <h2 className="font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
        Ask the law. <span className="text-brand-500">Get the citation.</span>
      </h2>
      <p className="mt-3 max-w-lg text-[14px] leading-relaxed text-white/50">
        Isla AI answers from seven real Philippine privacy instruments, quoted span by span. If the
        evidence is thin it refuses rather than guessing.
      </p>

      <div className="mt-8 grid w-full max-w-2xl gap-2 sm:grid-cols-3">
        {SUGGESTIONS.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.title}
              type="button"
              onClick={() => onPick(s.q)}
              className="group rounded-xl border border-white/8 bg-white/[0.02] p-4 text-left transition-colors hover:border-brand-500/40 hover:bg-brand-500/[0.07]"
            >
              <Icon
                className="mb-2.5 size-4 text-brand-400 transition-colors group-hover:text-brand-300"
                aria-hidden="true"
              />
              <span className="block text-[13px] font-medium text-white/85">{s.title}</span>
              <span className="mt-1 block text-[11px] leading-snug text-white/40">{s.q}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}