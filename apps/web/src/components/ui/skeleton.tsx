import { cn } from "@/lib/utils";

/**
 * Loading placeholder. Uses a CSS animation rather than a component state so a
 * skeleton can be swapped for real content without a layout jump.
 */
export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-white/[0.07]", className)}
      {...props}
    />
  );
}

/** Three dots that indicate a request is in flight. */
export function TypingDots({ label = "Isla AI is thinking" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-white/50">
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-brand-500"
            style={{ animationDelay: `${i * 140}ms`, animationDuration: "1.1s" }}
          />
        ))}
      </span>
      <span className="sr-only">{label}</span>
    </span>
  );
}