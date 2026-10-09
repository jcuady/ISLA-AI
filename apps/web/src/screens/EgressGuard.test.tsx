import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EgressGuard from "@/screens/EgressGuard";
import type { ScanResult } from "@/lib/api";

function scan(over: Partial<ScanResult> = {}): ScanResult {
  return {
    original: "Contact Maria at 0917 123 4567 re ACCT 0056-12345678",
    redacted: "Contact [PHONE_PH] re ACCT [ACCOUNT_NO]",
    verdict: "BLOCK_ESCALATE",
    verdict_label: "Block and escalate",
    verified_clean: false,
    residual_leakage: 0,
    passes: 3,
    latency_ms: 0.2,
    notes: ["3 verification passes", "0.00% residual leakage"],
    redaction_map: [],
    entities: [
      {
        type: "PH_MOBILE",
        start: 11,
        end: 24,
        text: "0917 123 4567",
        score: 0.99,
        stage: "regex",
        validated: true,
        reasons: ["luhn:pass", "prefix:globe"],
      },
    ],
    entity_counts: { PH_MOBILE: 1 },
    ...over,
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

let impl: (url: string, init?: RequestInit) => Promise<Response>;
let calls: Array<{ url: string; body: unknown }> = [];

beforeEach(() => {
  calls = [];
  impl = async (url) => {
    if (url === "/api/sample") return fakeResponse({ sample: "SAMPLE_PAYLOAD" });
    return fakeResponse(scan());
  };
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    let body: unknown;
    try {
      body = JSON.parse(String(init?.body ?? "null"));
    } catch {
      body = undefined;
    }
    calls.push({ url, body });
    return impl(url, init);
  });
});

afterEach(() => vi.restoreAllMocks());

/** Render and wait for the mount-time sample load to settle. */
async function mount() {
  render(<EgressGuard />);
  await waitFor(() =>
    expect(screen.getByLabelText("Text to scan for personal information")).toBeInTheDocument(),
  );
}

const paste = async (text: string) => {
  const user = userEvent.setup();
  const box = screen.getByLabelText("Text to scan for personal information");
  await user.clear(box);
  if (text) await user.type(box, text);
  return user;
};

describe("EgressGuard", () => {
  it("opens with a sample already loaded, so the demo is never a blank box", async () => {
    render(<EgressGuard />);
    await waitFor(() =>
      expect(screen.getByLabelText("Text to scan for personal information")).toHaveValue(
        "SAMPLE_PAYLOAD",
      ),
    );
  });

  it("shows an empty verdict panel before any scan", async () => {
    render(<EgressGuard />);
    expect(screen.getByText(/No scan yet/)).toBeInTheDocument();
  });

  it("runs a scan and shows both the original and the redacted text", async () => {
    await mount();
    const user = await paste("Contact Maria at 0917 123 4567");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    await waitFor(() => expect(screen.getByTestId("pane-original")).toBeInTheDocument());
    expect(screen.getByTestId("pane-original")).toHaveTextContent("0917 123 4567");
    expect(screen.getByTestId("pane-redacted")).toHaveTextContent("[PHONE_PH]");
    expect(calls.at(-1)).toEqual({
      url: "/api/pii/redact",
      body: { text: "Contact Maria at 0917 123 4567" },
    });
  });

  it("renders BLOCK in the block tone with a visible label", async () => {
    await mount();
    const user = await paste("sensitive");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    const badge = await screen.findByText("Block and escalate");
    expect(badge).toBeInTheDocument();
    expect(badge.closest("[role='status']")).toBeInTheDocument();
  });

  it("renders SAFE_TO_SEND without borrowing BLOCK's treatment", async () => {
    impl = async (url) =>
      url === "/api/sample"
        ? fakeResponse({ sample: "ok" })
        : fakeResponse(
            scan({ verdict: "SAFE_TO_SEND", verdict_label: "Safe to send", entities: [] }),
          );
    await mount();
    const user = await paste("clean");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    const badge = await screen.findByText("Safe to send");
    const cls = badge.closest("[role='status']")?.getAttribute("class") ?? "";
    expect(cls).toContain("semantic-safe");
    expect(cls).not.toContain("semantic-block");
  });

  it("shows measured residual leakage, latency and pass count", async () => {
    await mount();
    const user = await paste("sensitive");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    expect(await screen.findByText("0.00%")).toBeInTheDocument();
    expect(screen.getByText("0 ms")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Entities")).toBeInTheDocument();
  });

  it("flags non-zero residual leakage rather than rounding it away", async () => {
    impl = async (url) =>
      url === "/api/sample"
        ? fakeResponse({ sample: "ok" })
        : fakeResponse(scan({ residual_leakage: 0.0123 }));
    await mount();
    const user = await paste("sensitive");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    expect(await screen.findByText("1.23%")).toBeInTheDocument();
  });

  it("lists every detected entity with its type", async () => {
    await mount();
    const user = await paste("sensitive");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    expect(await screen.findByText("Detected (1)")).toBeInTheDocument();
    expect(screen.getByText("PH_MOBILE")).toBeInTheDocument();
    expect(screen.getByText("0917 123 4567")).toBeInTheDocument();
  });

  it("does not crash when the engine returns no notes array", async () => {
    impl = async (url) =>
      url === "/api/sample"
        ? fakeResponse({ sample: "ok" })
        : fakeResponse(scan({ notes: undefined as unknown as string[] }));
    await mount();
    const user = await paste("sensitive");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));
    expect(await screen.findByTestId("pane-original")).toBeInTheDocument();
  });

  it("reports a failed scan and keeps the pasted text for a retry", async () => {
    impl = async (url) => {
      if (url === "/api/sample") return fakeResponse({ sample: "x" });
      throw new Error("500 Internal Server Error");
    };
    await mount();
    const user = await paste("keep me");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));

    expect(await screen.findByText("Scan failed")).toBeInTheDocument();
    expect(screen.getByText(/500 Internal Server Error/)).toBeInTheDocument();
    expect(screen.getByLabelText("Text to scan for personal information")).toHaveValue(
      "keep me",
    );
  });

  it("disables Scan on empty input rather than sending a pointless request", async () => {
    await mount();
    await paste("");
    expect(screen.getByRole("button", { name: "Scan & redact" })).toBeDisabled();
    expect(calls.filter((c) => c.url === "/api/pii/redact")).toHaveLength(0);
  });

  it("scans immediately when a sample chip is chosen", async () => {
    await mount();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Payment note" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/pii/redact")).toBe(true));
  });

  it("clears the text, the verdict and the error together", async () => {
    await mount();
    const user = await paste("secret");
    await user.click(screen.getByRole("button", { name: "Scan & redact" }));
    await screen.findByTestId("pane-original");

    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.getByLabelText("Text to scan for personal information")).toHaveValue("");
    expect(screen.queryByTestId("pane-original")).not.toBeInTheDocument();
    expect(screen.getByText(/No scan yet/)).toBeInTheDocument();
  });
});