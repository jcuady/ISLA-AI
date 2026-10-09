import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge, verdictTone, type StatusTone } from "@/components/ui/status-badge";

describe("verdictTone", () => {
  it("maps each Egress Guard verdict to its own tone", () => {
    expect(verdictTone("SAFE_TO_SEND")).toBe("safe");
    expect(verdictTone("REDACT_THEN_SEND")).toBe("caution");
    expect(verdictTone("BLOCK_ESCALATE")).toBe("block");
  });

  it("falls back to neutral for an unrecognised verdict rather than guessing", () => {
    expect(verdictTone("MAYBE")).toBe("neutral");
    expect(verdictTone("")).toBe("neutral");
  });
});

describe("StatusBadge", () => {
  const tones: StatusTone[] = ["safe", "caution", "block", "refuse", "info", "neutral"];

  it("always renders the visible label, because colour alone is not a signal", () => {
    render(<StatusBadge tone="block" label="Block and escalate" />);
    expect(screen.getByText("Block and escalate")).toBeInTheDocument();
  });

  it("exposes the tone as a status role for assistive technology", () => {
    render(<StatusBadge tone="safe" label="Safe to send" />);
    expect(screen.getByRole("status")).toHaveTextContent("Safe to send");
  });

  it("gives every tone a distinct icon, so tones survive desaturation", () => {
    const icons = tones.map((tone) => {
      const { container, unmount } = render(
        <StatusBadge tone={tone} label={tone} data-testid="badge" />,
      );
      const glyph = container.querySelector("svg");
      expect(glyph).not.toBeNull();
      // lucide renders a class per icon; a repeat means two tones share a glyph.
      const sig = glyph!.getAttribute("class") ?? "";
      unmount();
      return sig;
    });
    expect(new Set(icons).size).toBe(tones.length);
  });

  it("gives every tone a distinct colour treatment", () => {
    const classes = tones.map((tone) => {
      const { container, unmount } = render(<StatusBadge tone={tone} label={tone} />);
      const cls = container.firstElementChild?.getAttribute("class") ?? "";
      unmount();
      return cls;
    });
    expect(new Set(classes).size).toBe(tones.length);
  });

  it("renders BLOCK with a heavier border than the other tones", () => {
    const { container } = render(<StatusBadge tone="block" label="Block" />);
    const cls = container.firstElementChild?.getAttribute("class") ?? "";
    // /70 opacity on the border is BLOCK's loud, unmistakable form.
    expect(cls).toContain("border-semantic-block/70");
  });

  it("accepts an override icon", () => {
    render(<StatusBadge tone="info" label="Custom" icon={<span>★</span>} />);
    expect(screen.getByText("★")).toBeInTheDocument();
  });
});