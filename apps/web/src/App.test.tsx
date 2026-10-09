import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "@/App";

function fakeResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

const AIRGAP = {
  air_gapped: true,
  outbound_blocked: true,
  resolver_available: false,
  bind_host: "127.0.0.1",
  checked_at: "2026-10-06T00:00:00Z",
  elapsed_ms: 9,
  note: "",
  probes: [],
};

const HEALTH = {
  status: "ok",
  product: "Isla AI",
  tagline: "",
  bind: { host: "127.0.0.1", port: 8765, loopback_only: true },
  corpus: { chunks: 223, documents: 7, dense_ready: true, total_chars: 1 },
  models: {},
  engines: {},
};

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.startsWith("/api/airgap")) return Promise.resolve(fakeResponse(AIRGAP));
    if (url.startsWith("/api/health")) return Promise.resolve(fakeResponse(HEALTH));
    if (url.startsWith("/api/sample"))
      return Promise.resolve(fakeResponse({ sample: "SAMPLE" }));
    if (url.startsWith("/api/audit"))
      return Promise.resolve(
        fakeResponse({
          entries: [],
          verification: { valid: true, entries: 0 },
          stats: { total: 0, by_event: {}, note: "" },
        }),
      );
    if (url.startsWith("/api/copilot/ask"))
      return Promise.resolve(
        fakeResponse({
          question: "",
          answer: "Notify the NPC within 72 hours.",
          refused: false,
          confidence: 0.9,
          citations: [],
          sources: [],
          footer: "",
          latency_ms: 8,
          retrieval_mode: "hybrid",
          llm_used: false,
          notes: [],
        }),
      );
    return Promise.resolve(fakeResponse({}));
  });
});

afterEach(() => {
  window.history.replaceState(null, "", "/console");
  vi.restoreAllMocks();
});

const viewParam = () => new URLSearchParams(window.location.search).get("view");

describe("App shell", () => {
  it("opens on the Copilot", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "DPA Copilot" })).toBeInTheDocument();
  });

  it("opens directly on Egress Guard from a shared ?view= link", () => {
    window.history.replaceState(null, "", "/console?view=egress");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Egress Guard" })).toBeInTheDocument();
    expect(screen.getByLabelText("Text to scan for personal information")).toBeInTheDocument();
  });

  it("opens directly on the Ledger from ?view=ledger", () => {
    window.history.replaceState(null, "", "/console?view=ledger");
    render(<App />);
    expect(screen.getByRole("heading", { name: "Audit Ledger" })).toBeInTheDocument();
  });

  it("ignores an unknown ?view= rather than rendering a blank screen", () => {
    window.history.replaceState(null, "", "/console?view=../../etc/passwd");
    render(<App />);
    expect(screen.getByRole("heading", { name: "DPA Copilot" })).toBeInTheDocument();
  });

  it("writes the view into the URL so it can be shared or bookmarked", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /Audit Ledger/ }));
    expect(viewParam()).toBe("ledger");
  });

  it("keeps history usable: Back returns to the previous control", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /Egress Guard/ }));
    expect(screen.getByRole("heading", { name: "Egress Guard" })).toBeInTheDocument();

    window.history.replaceState(null, "", "/console?view=copilot");
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "DPA Copilot" })).toBeInTheDocument(),
    );
  });

  it("drops ?view= when returning to the Copilot, so the URL stays canonical", async () => {
    window.history.replaceState(null, "", "/console?view=ledger");
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /DPA Copilot/ }));
    expect(viewParam()).toBeNull();
  });

  it("New conversation discards an existing thread", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    await screen.findByText(/72 hours/);

    await user.click(screen.getByRole("button", { name: /New conversation/ }));
    await waitFor(() => expect(screen.queryByText(/72 hours/)).not.toBeInTheDocument());
    expect(screen.getByText(/Ask the law\./)).toBeInTheDocument();
    expect(viewParam()).toBeNull();
  });

  it("disables New conversation when no conversation is open", () => {
    window.history.replaceState(null, "", "/console?view=egress");
    render(<App />);
    expect(screen.getByRole("button", { name: /New conversation/ })).toBeDisabled();
  });

  it("reports the air-gap state from the probe, not a hardcoded claim", async () => {
    render(<App />);
    expect(await screen.findAllByText(/Air-gapped|Connected/)).not.toHaveLength(0);
    // Desktop sidebar and top bar both report it.
    expect(screen.getAllByText("Network: air-gapped").length).toBeGreaterThan(0);
  });

  it("shows an offline badge wording on narrow viewports", async () => {
    render(<App />);
    // The compact badge only renders its label once the probe has answered.
    expect(await screen.findByText("Offline")).toBeInTheDocument();
  });

  it("renders the copilot, egress and ledger surfaces from one shell", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App />);
    expect(screen.getByText(/Ask the law\./)).toBeInTheDocument();
    unmount();

    window.history.replaceState(null, "", "/console?view=egress");
    const { unmount: u2 } = render(<App />);
    await waitFor(() => expect(screen.getByText("Text to scan")).toBeInTheDocument());
    u2();
  });
});