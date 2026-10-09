import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FraudRisk from "./FraudRisk";

const calls: Array<{ url: string; body: unknown }> = [];

function stub(overrides: Record<string, unknown> = {}) {
  calls.length = 0;
  vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
    calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    if (url === "/api/risk/indicators") {
      return new Response(
        JSON.stringify({
          count: 1,
          coverage_gap: ["BSP - Manual of Regulations for Banks, not in this corpus."],
          indicators: [
            {
              id: "structuring",
              label: "Structuring",
              tier: "high",
              exposure: ["bank"],
              why: "Why it matters.",
              action: "Escalate to the MLRO.",
              regulator: "AMLC",
              legal_hook: { doc_id: "RA-9160", anchor: "covered transaction", is_gap: false },
            },
          ],
        }),
        { status: 200 },
      );
    }
    if (url === "/api/risk/assess") {
      return new Response(
        JSON.stringify({
          tier: "critical",
          risk_tier: "critical",
          exposed: ["bank", "customer"],
          red_flags: [
            {
              id: "mule_account",
              label: "Money-mule account",
              tier: "critical",
              exposure: ["both"],
              evidence: "student account received 480,000 in cash",
              why: "A pass-through account is the common retail laundering pattern.",
              action: "Escalate to the MLRO the same day.",
              regulator: "AMLC / BSP",
              legal_hook: {
                doc_id: "GAP",
                anchor: "BSP - Manual of Regulations for Banks",
                is_gap: true,
              },
              citation: null,
            },
          ],
          required_actions: ["Escalate to the MLRO the same day."],
          summary: "CRITICAL risk. 1 indicator matched.",
          coverage_gap: ["BSP - Manual of Regulations for Banks, not in this corpus."],
          citation_count: 0,
          degraded: true,
          footer: "Not a substitute for your compliance officer.",
          latency_ms: 8.4,
          ...overrides,
        }),
        { status: 200 },
      );
    }
    return new Response("{}", { status: 404 });
  });
}

describe("FraudRisk", () => {
  beforeEach(() => stub());

  it("offers the scenario box and a run control, neither of them a dead end", async () => {
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "cash deposits then a wire abroad");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getAllByText(/CRITICAL/i).length).toBeGreaterThan(0));
    expect(calls.some((c) => c.url === "/api/risk/assess")).toBe(true);
  });

  it("posts the scenario under the key the API expects", async () => {
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "hello");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/risk/assess")).toBe(true));
    const call = calls.find((c) => c.url === "/api/risk/assess");
    // Compared as serialised JSON: TextRequest takes `text`, and a wrong key
    // returns HTTP 422 rather than a helpful message, so this is worth pinning.
    expect(JSON.stringify(call?.body)).toBe(JSON.stringify({ text: "hello" }));
  });

  it("shows the tier, who is exposed, and the evidence that fired", async () => {
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "mule");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getAllByText(/CRITICAL/i).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/student account received 480,000 in cash/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/customer/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/\bbank\b/i).length).toBeGreaterThan(0);
  });

  it("names the coverage gap instead of implying full coverage", async () => {
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "mule");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getAllByText(/CRITICAL/i).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/not in this corpus/i).length).toBeGreaterThan(0);
  });

  it("labels a gap hook as a gap rather than as a citation", async () => {
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "mule");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getAllByText(/CRITICAL/i).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/not in corpus|not quoted|could not be retrieved/i).length)
      .toBeGreaterThan(0);
  });

  it("reports a clean scenario without inventing red flags", async () => {
    stub({ tier: "none", risk_tier: "none", exposed: [], red_flags: [], citation_count: 0 });
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "ordinary withdrawal");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getByText(/no red-flag/i)).toBeInTheDocument());
    expect(screen.queryByText(/mule_account/)).not.toBeInTheDocument();
  });

  it("surfaces a server error instead of pretending the screen was clean", async () => {
    vi.stubGlobal("fetch", async () => new Response("nope", { status: 500 }));
    render(<FraudRisk />);
    const box = await screen.findByRole("textbox", { name: /scenario/i });
    await userEvent.clear(box);
    await userEvent.type(box, "boom");
    await userEvent.click(screen.getByRole("button", { name: /screen|assess|run/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("loads the indicator catalogue so the UI cannot invent a red flag", async () => {
    render(<FraudRisk />);
    await waitFor(() => expect(calls.some((c) => c.url === "/api/risk/indicators")).toBe(true));
  });
});