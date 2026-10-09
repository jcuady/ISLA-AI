import * as React from "react";
import { ArrowUp, Square, Paperclip, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

/**
 * Auto-resizing composer, adapted from the v0-style reference.
 *
 * Two deliberate changes from the reference, both of which matter in a
 * compliance tool rather than a demo:
 *
 *  1. The reference cleared the field and reset its height on Enter but never
 *     emitted the value - it was a static mock. Here Enter (without Shift)
 *     actually submits, and the send button is disabled on empty input.
 *  2. The reference had no pending state. A bank officer pasting a customer
 *     record needs to be able to STOP a request, so the button becomes a stop
 *     control while in flight and Escape cancels.
 */

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  onStop?: () => void;
  busy?: boolean;
  placeholder?: string;
  disabled?: boolean;
  /** Rendered under the composer, e.g. the disclosure footer. */
  footer?: React.ReactNode;
  autoFocus?: boolean;
  className?: string;
  inputRef?: React.RefObject<HTMLTextAreaElement>;
}

const MIN_HEIGHT = 24;
const MAX_HEIGHT = 200;

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  busy = false,
  placeholder = "Ask about the Data Privacy Act…",
  disabled = false,
  footer,
  autoFocus,
  className,
  inputRef,
}: ChatComposerProps) {
  const localRef = React.useRef<HTMLTextAreaElement>(null);
  const ref = inputRef ?? localRef;

  // Grow with content up to MAX_HEIGHT, then scroll. Shrinking first is what
  // makes scrollHeight accurate.
  const adjustHeight = React.useCallback((reset = false) => {
    const el = ref.current;
    if (!el) return;
    if (reset) {
      el.style.height = `${MIN_HEIGHT}px`;
      return;
    }
    el.style.height = "auto";
    el.style.height = `${Math.min(Math.max(el.scrollHeight, MIN_HEIGHT), MAX_HEIGHT)}px`;
  }, [ref]);

  React.useEffect(() => {
    adjustHeight(true);
  }, [adjustHeight]);

  // A new answer changes the hint text length; keep the box sized correctly.
  React.useEffect(() => {
    adjustHeight();
  }, [placeholder, adjustHeight]);

  React.useEffect(() => {
    const onResize = () => adjustHeight();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [adjustHeight]);

  const canSend = value.trim().length > 0 && !disabled && !busy;

  const submit = React.useCallback(() => {
    if (!canSend) return;
    onSubmit(value.trim());
    onChange("");
    adjustHeight(true);
  }, [canSend, onSubmit, onChange, value, adjustHeight]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
      return;
    }
    // Escape stops an in-flight request rather than clearing the draft, so a
    // half-typed question survives an accidental keypress.
    if (e.key === "Escape" && busy) {
      e.preventDefault();
      onStop?.();
    }
  };

  return (
    <div className={cn("w-full", className)}>
      <div
        className={cn(
          "relative rounded-composer border bg-noir-900/80 backdrop-blur-sm transition-colors",
          disabled
            ? "border-white/8 opacity-60"
            : "border-white/10 focus-within:border-brand-500/50",
        )}
      >
        <Textarea
          ref={ref}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            adjustHeight();
          }}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          autoFocus={autoFocus}
          aria-label="Message KALIX"
          className="max-h-[200px] overflow-y-auto border-0 bg-transparent px-4 py-3.5 pr-4 text-[15px] leading-relaxed placeholder:text-white/30 focus:outline-none"
          style={{ minHeight: MIN_HEIGHT, height: MIN_HEIGHT }}
        />

        <div className="flex items-center justify-between gap-2 px-2.5 pb-2.5 pt-1">
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              disabled
              title="File attachment is not available in an air-gapped build"
              className="cursor-not-allowed opacity-45"
            >
              <Paperclip className="size-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Attach</span>
            </Button>
          </div>

          <div className="flex items-center gap-2">
            {value.length > 0 && !busy && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  onChange("");
                  adjustHeight(true);
                  ref.current?.focus();
                }}
                className="text-white/45"
              >
                <RotateCcw className="size-3.5" aria-hidden="true" />
                <span className="sr-only">Clear draft</span>
              </Button>
            )}

            {busy ? (
              <Button
                variant="secondary"
                size="icon"
                onClick={() => onStop?.()}
                aria-label="Stop generating"
                title="Stop (Esc)"
                className="border-white/15"
              >
                <Square className="size-3.5 fill-current" aria-hidden="true" />
              </Button>
            ) : (
              <Button
                size="icon"
                onClick={submit}
                disabled={!canSend}
                aria-label="Send message"
                title="Send (Enter)"
              >
                <ArrowUp className="size-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {footer}
    </div>
  );
}