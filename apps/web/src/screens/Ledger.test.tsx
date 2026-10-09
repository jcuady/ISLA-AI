import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Ledger from "@/screens/Ledger";
import type { LedgerEntry } from "@/lib/api";

function entry(seq: number, event: string): LedgerEntry {
  return {
    seq,
    ts: "2026-10-06T09:15:00Z",
    event,
    summary: { entities: 3 },
    prev_hash: "a".repeat(64),
    entry_hash: "b".repeat(64),
  };
}

function fakeResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

let impl: (url: string) => Promise<Response>;
let urls: string[] = [];

beforeEach(() => {
  urls = [];
  impl = async () =>
    fakeResponse({
      entries: [entry(441, "pii.redact"), entry(440, "copilot.ask")],
      verification: { valid: true, entries: 441, head: "b".repeat(64) },
      stats: { total: 441, by_event: { "pii.redact": 12, "copilot.ask": 8 }, note: "" },
    });
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    urls.push(url);
    return impl(url);
  });
});

afterEach(() => vi.restoreAllMocks());

describe("Ledger", () => {
  it("loads and verifies the chain on mount", async () => {
    render(<Ledger />);
    expect(await screen.findByText("Chain verified")).toBeInTheDocument();
    expect(urls[0]).toBe("/api/audit?limit=50");
  });

  it("states the entry count, so the proof is quantified", async () => {
    render(<Ledger />);
    expect(await screen.findByText(/441 entries, each SHA-256 linked/)).toBeInTheDocument();
  });

  it("says which entry broke the chain instead of a vague failure", async () => {
    impl = async () =>
      fakeResponse({
        entries: [entry(12, "pii.redact")],
        verification: { valid: false, entries: 12, broken_at: 9 },
        stats: { total: 12, by_event: {}, note: "" },
      });
    render(<Ledger />);
    expect(await screen.findByText("Chain broken")).toBeInTheDocument();
    expect(screen.getByText(/at entry 9/)).toBeInTheDocument();
  });

  it("never shows a green verified state when verification fails", async () => {
    impl = async () =>
      fakeResponse({
        entries: [],
        verification: { valid: false, entries: 0 },
        stats: { total: 0, by_event: {}, note: "" },
      });
    render(<Ledger />);
    await screen.findByText("Chain broken");
    expect(screen.queryByText("Chain verified")).not.toBeInTheDocument();
  });

  it("explains what is stored and what is never stored", async () => {
    render(<Ledger />);
    expect(screen.getByText("Counts and verdicts")).toBeInTheDocument();
    expect(screen.getByText("Never customer text")).toBeInTheDocument();
  });

  it("renders each entry with its sequence number and event", async () => {
    render(<Ledger />);
    await screen.findByText("Chain verified");
    expect(screen.getByText("#441")).toBeInTheDocument();
    expect(screen.getByText("pii.redact")).toBeInTheDocument();
  });

  it("reports how much of the ledger is being shown", async () => {
    render(<Ledger />);
    await screen.findByText("Chain verified");
    expect(screen.getByText("showing 2 of 441")).toBeInTheDocument();
  });

  it("truncates hashes for display but keeps them in the tooltip", async () => {
    render(<Ledger />);
    await screen.findByText("Chain verified");
    expect(screen.getAllByText("bbbbbbbbbb").length).toBeGreaterThan(0);
  });

  it("re-verifies on demand", async () => {
    const user = userEvent.setup();
    render(<Ledger />);
    await screen.findByText("Chain verified");
    expect(urls).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Re-verify" }));
    await waitFor(() => expect(urls).toHaveLength(2));
  });

  it("surfaces a fetch failure instead of showing an empty ledger", async () => {
    impl = async () => {
      throw new Error("500 Internal Server Error");
    };
    render(<Ledger />);
    expect(await screen.findByText("Ledger unavailable")).toBeInTheDocument();
    expect(screen.getByText(/500 Internal Server Error/)).toBeInTheDocument();
  });

  it("handles an empty ledger without crashing", async () => {
    impl = async () =>
      fakeResponse({
        entries: [],
        verification: { valid: true, entries: 0 },
        stats: { total: 0, by_event: {}, note: "" },
      });
    render(<Ledger />);
    expect(await screen.findByText("No entries yet.")).toBeInTheDocument();
  });
});