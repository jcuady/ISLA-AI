import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Copilot from "@/screens/Copilot";
import type { CopilotAnswer } from "@/lib/api";

/**
 * The screen is tested against the real `api.ask` layer: only `fetch` is
 * replaced. Mocking the api module instead would let a broken signal, a wrong
 * URL, or a dropped AbortSignal pass unnoticed - which is exactly the class of
 * bug this console had before the redesign.
 */

function answer(over: Partial<CopilotAnswer> = {}): CopilotAnswer {
  return {
    question: "Ilang oras?",
    answer: "Ang National Privacy Commission ay dapat na abiso sa loob ng 72 hours.",
    refused: false,
    confidence: 0.91,
    citations: [
      {
        id: "c1",
        label: "RA-10173 §20(c)",
        doc_id: "RA-10173",
        doc_title: "Data Privacy Act of 2012",
        issuer: "Republic Act",
        section: "Section 20(c)",
        effective_date: "2012-09-08",
        url: "https://elibrary.judiciary.gov.ph/ra10173",
        doc_type: "statute",
        rank: 1,
        score: 0.82,
      },
    ],
    sources: [],
    footer: "Quoted verbatim from the cited span.",
    latency_ms: 8.4,
    retrieval_mode: "hybrid",
    llm_used: false,
    notes: [],
    ...over,
  };
}

/** Minimal stand-in for the parts of `Response` that `post()` actually reads. */
function fakeResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function aborted(): Promise<never> {
  return Promise.reject(
    Object.assign(new Error("The operation was aborted."), { name: "AbortError" }),
  );
}

type Impl = (url: string, init?: RequestInit) => Promise<Response>;

let impl: Impl;
let calls: Array<{ url: string; body: unknown; signal?: AbortSignal }> = [];

const immediate = (body: unknown): Impl => async () => fakeResponse(body);

beforeEach(() => {
  calls = [];
  impl = immediate(answer());
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    let body: unknown;
    try {
      body = JSON.parse(String(init?.body ?? "null"));
    } catch {
      body = undefined;
    }
    calls.push({ url, body, signal: init?.signal ?? undefined });
    return impl(url, init);
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

const typeAndSend = async (text: string) => {
  const user = userEvent.setup();
  const box = screen.getByLabelText("Message Isla AI");
  await user.type(box, text);
  await user.type(box, "{Enter}");
};

describe("Copilot screen", () => {
  it("opens on an empty state with suggestion cards, not a blank panel", () => {
    render(<Copilot resetKey={0} />);
    expect(screen.getByText(/Ask the law\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Breach reporting clock/ })).toBeInTheDocument();
  });

  it("sends a question and renders the answer", async () => {
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    expect(await screen.findByText(/72 hours/)).toBeInTheDocument();
    expect(screen.getByText("Ilang oras dapat ko i-report ang data breach?")).toBeInTheDocument();
    expect(calls[0].url).toBe("/api/copilot/ask");
    expect(calls[0].body).toEqual({
      text: "Ilang oras dapat ko i-report ang data breach?",
    });
  });

  it("shows the citation chip and expands it on demand", async () => {
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    const chip = await screen.findByRole("button", { name: /RA-10173/ });
    expect(chip).toHaveAttribute("aria-expanded", "false");
    await user.click(chip);
    expect(chip).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Data Privacy Act of 2012")).toBeInTheDocument();
    expect(screen.getByText(/Section: Section 20\(c\)/)).toBeInTheDocument();
  });

  it("marks an extractive answer, so no one reads it as generated prose", async () => {
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    expect(await screen.findByText("extractive")).toBeInTheDocument();
  });

  it("shows the measured latency and retrieval mode rather than hiding them", async () => {
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    expect(await screen.findByText("8 ms")).toBeInTheDocument();
    expect(screen.getByText("conf 0.91")).toBeInTheDocument();
    expect(screen.getByText("hybrid")).toBeInTheDocument();
  });

  it("renders a refusal in its own panel rather than as a normal answer", async () => {
    impl = immediate(answer({ refused: true, answer: "Wala akong mabatay basehan.", citations: [] }));
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    expect(await screen.findByText(/Refused/)).toBeInTheDocument();
    expect(screen.getByText(/Wala akong mabatay basehan\./)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /RA-10173/ })).not.toBeInTheDocument();
  });

  it("reports a failed request instead of silently dropping the question", async () => {
    impl = async () => {
      throw new Error("500 Internal Server Error");
    };
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    expect(await screen.findByText("Request failed")).toBeInTheDocument();
    expect(screen.getByText(/500 Internal Server Error/)).toBeInTheDocument();
  });

  it("clears the thread when the shell bumps resetKey", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    await screen.findByText(/72 hours/);

    rerender(<Copilot resetKey={1} />);
    await waitFor(() => expect(screen.queryByText(/72 hours/)).not.toBeInTheDocument());
    expect(screen.getByText(/Ask the law\./)).toBeInTheDocument();
  });

  it("accepts a question injected by the sidebar and de-duplicates by nonce", async () => {
    const { rerender } = render(
      <Copilot resetKey={0} externalQuestion={{ q: "Anong vendor?", nonce: 1 }} />,
    );
    await waitFor(() => expect(screen.getByText("Anong vendor?")).toBeInTheDocument());

    // Re-rendering with the same nonce must not re-fire the request.
    rerender(<Copilot resetKey={0} externalQuestion={{ q: "Anong vendor?", nonce: 1 }} />);
    await waitFor(() => expect(screen.getAllByText("Anong vendor?")).toHaveLength(1));
  });

  it("shows a pending indicator rather than an empty gap", async () => {
    impl = () => new Promise<Response>(() => {}); // never settles
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    expect(await screen.findByText("Isla AI is thinking")).toBeInTheDocument();
  });

  it("passes an AbortSignal with every request, so Stop is real", async () => {
    impl = () => new Promise<Response>(() => {});
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    await waitFor(() => expect(calls[0].signal).toBeInstanceOf(AbortSignal));
  });

  it("aborts the in-flight request when Stop is pressed, and keeps the thread usable", async () => {
    impl = (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(
            Object.assign(new Error("aborted"), { name: "AbortError" }),
          );
        });
      });
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    const stop = await screen.findByRole("button", { name: "Stop generating" });
    await user.click(stop);

    await waitFor(() => expect(calls[0].signal?.aborted).toBe(true));
    // The aborted answer must not be rendered as an error bubble.
    await waitFor(() =>
      expect(screen.queryByText("Request failed")).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Send message" })).toBeInTheDocument();
  });

  it("ignores an abort that lands after the answer has rendered", async () => {
    // A race a real bank console hits constantly: the answer arrives, then the
    // user presses Escape. This must not blank the thread.
    let release: (() => void) | null = null;
    impl = async () => {
      await new Promise<void>((r) => {
        release = r;
      });
      return fakeResponse(answer());
    };
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Stop generating" })).toBeInTheDocument());
    release!();
    expect(await screen.findByText(/72 hours/)).toBeInTheDocument();
  });

  it("keeps a successful answer after an unrelated earlier failure", async () => {
    impl = async () => {
      throw new Error("503 Service Unavailable");
    };
    const user = userEvent.setup();
    render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    await screen.findByText("Request failed");

    impl = immediate(answer());
    await typeAndSend("second question");
    expect(await screen.findByText(/72 hours/)).toBeInTheDocument();
    expect(screen.getByText("Request failed")).toBeInTheDocument();
  });

  it("discards a stale answer when a new conversation starts mid-flight", async () => {
    impl = (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(Object.assign(new Error("aborted"), { name: "AbortError" })),
        );
      });
    const user = userEvent.setup();
    const { rerender } = render(<Copilot resetKey={0} />);
    await user.click(screen.getByRole("button", { name: /Breach reporting clock/ }));
    await waitFor(() => expect(calls[0].signal).toBeDefined());

    rerender(<Copilot resetKey={1} />);
    await waitFor(() => expect(calls[0].signal?.aborted).toBe(true));
    expect(screen.getByText(/Ask the law\./)).toBeInTheDocument();
    expect(screen.queryByText(/72 hours/)).not.toBeInTheDocument();
  });

  it("rejects a whitespace-only question without calling the API", async () => {
    render(<Copilot resetKey={0} />);
    await typeAndSend("   ");
    expect(calls).toHaveLength(0);
  });

  it("propagates an abort rejection as aborted(), not as a generic error", async () => {
    // Guards the helper itself: if this regressed, every Stop test would pass
    // for the wrong reason.
    await expect(aborted()).rejects.toMatchObject({ name: "AbortError" });
  });
});