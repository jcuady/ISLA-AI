import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppSidebar, NAV_ITEMS, ViewIcon } from "@/components/app-sidebar";
import type { AirgapResult, Health } from "@/lib/api";

const health: Health = {
  status: "ok",
  product: "KALIX",
  tagline: "t",
  bind: { host: "127.0.0.1", port: 8765, loopback_only: true },
  corpus: { chunks: 223, documents: 7, dense_ready: false, total_chars: 1 },
  models: {},
  engines: {},
};

const gap = (over: Partial<AirgapResult> = {}): AirgapResult => ({
  air_gapped: true,
  outbound_blocked: true,
  resolver_available: false,
  bind_host: "127.0.0.1",
  checked_at: "2026-10-06T00:00:00Z",
  elapsed_ms: 12,
  note: "",
  probes: [],
  ...over,
});

function setup(props: Partial<React.ComponentProps<typeof AppSidebar>> = {}) {
  const onNavigate = vi.fn();
  const onNewChat = vi.fn();
  const onStarter = vi.fn();
  render(
    <AppSidebar
      active="copilot"
      onNavigate={onNavigate}
      gap={gap()}
      gapError={null}
      health={health}
      onNewChat={onNewChat}
      canNewChat
      onStarter={onStarter}
      {...props}
    />,
  );
  return { onNavigate, onNewChat, onStarter };
}

describe("AppSidebar", () => {
  it("offers exactly the three shipped controls", () => {
    expect(NAV_ITEMS.map((n) => n.id)).toEqual(["copilot", "egress", "ledger"]);
  });

  it("marks the active view with aria-current", () => {
    setup({ active: "egress" });
    expect(screen.getByRole("button", { name: /Egress Guard/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: /DPA Copilot/ })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("navigates when a control is clicked", async () => {
    const user = userEvent.setup();
    const { onNavigate } = setup();
    await user.click(screen.getByRole("button", { name: /Audit Ledger/ }));
    expect(onNavigate).toHaveBeenCalledWith("ledger");
  });

  it("disables New conversation off the Copilot", () => {
    setup({ active: "ledger", canNewChat: false });
    expect(screen.getByRole("button", { name: /New conversation/ })).toBeDisabled();
  });

  it("starts a conversation from the Copilot", async () => {
    const user = userEvent.setup();
    const { onNewChat } = setup();
    await user.click(screen.getByRole("button", { name: /New conversation/ }));
    expect(onNewChat).toHaveBeenCalledTimes(1);
  });

  it("offers Taglish starter prompts on the Copilot only", async () => {
    const user = userEvent.setup();
    const onStarter = vi.fn();
    const { unmount } = render(
      <AppSidebar
        active="copilot"
        onNavigate={vi.fn()}
        gap={gap()}
        gapError={null}
        health={health}
        onNewChat={vi.fn()}
        canNewChat
        onStarter={onStarter}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Singapore/ }));
    expect(onStarter).toHaveBeenCalledTimes(1);
    unmount();

    setup({ active: "ledger" });
    expect(screen.queryByRole("button", { name: /Singapore/ })).not.toBeInTheDocument();
  });

  it("reports an air-gapped network in the safe tone", () => {
    setup({ gap: gap({ air_gapped: true }) });
    expect(screen.getByText("Network: air-gapped")).toBeInTheDocument();
  });

  it("does not claim air-gap when the probe found connectivity", () => {
    setup({ gap: gap({ air_gapped: false }) });
    expect(screen.getByText("Network: connected")).toBeInTheDocument();
  });

  it("surfaces a probe failure as an error rather than a green light", () => {
    setup({ gap: null, gapError: "probe timed out" });
    expect(screen.getByText("Probe error")).toBeInTheDocument();
  });

  it("surfaces corpus and bind facts for the demo", () => {
    setup();
    expect(screen.getByText("7 docs · 223 sections")).toBeInTheDocument();
    expect(screen.getByText("127.0.0.1 only")).toBeInTheDocument();
  });

  it("flags a non-loopback bind instead of hiding it", () => {
    setup({ health: { ...health, bind: { host: "0.0.0.0", port: 8765, loopback_only: false } } });
    expect(screen.getByText("UNEXPECTED")).toBeInTheDocument();
  });

  it("carries the legal disclaimer in the shell, not just the chat footer", () => {
    setup();
    expect(screen.getByText(/Not legal advice/)).toBeInTheDocument();
  });

  it("exports a matching icon per view", () => {
    for (const item of NAV_ITEMS) {
      const { container, unmount } = render(<ViewIcon id={item.id} />);
      expect(container.querySelector("svg")).not.toBeNull();
      unmount();
    }
  });
});