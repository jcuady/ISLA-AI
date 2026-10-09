import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import * as React from "react";
import { ChatComposer } from "@/components/ui/chat-composer";

function setup(overrides: Partial<React.ComponentProps<typeof ChatComposer>> = {}) {
  const onSubmit = vi.fn();
  const onChange = vi.fn();
  const onStop = vi.fn();
  const view = render(
    <ChatComposer
      value=""
      onChange={onChange}
      onSubmit={onSubmit}
      onStop={onStop}
      {...overrides}
    />,
  );
  return { ...view, onSubmit, onChange, onStop, box: screen.getByLabelText("Message KALIX") };
}

describe("ChatComposer", () => {
  it("submits on Enter", async () => {
    const user = userEvent.setup();
    const { onSubmit, box } = setup({ value: "Ilang oras?" });
    await user.type(box, "{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("Ilang oras?");
  });

  it("trims the value before emitting it", async () => {
    const user = userEvent.setup();
    const { onSubmit, box } = setup({ value: "  padded  " });
    await user.type(box, "{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("padded");
  });

  it("inserts a newline on Shift+Enter instead of submitting", async () => {
    const user = userEvent.setup();
    const { onSubmit, box } = setup({ value: "line one" });
    await user.type(box, "{Shift>}{Enter}{/Shift}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("does not submit whitespace-only input", async () => {
    const user = userEvent.setup();
    const { onSubmit, box } = setup({ value: "    " });
    await user.type(box, "{Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables send on empty input", () => {
    setup({ value: "" });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("enables send once there is text", () => {
    setup({ value: "hi" });
    expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled();
  });

  it("replaces send with a stop control while a request is in flight", () => {
    setup({ value: "hi", busy: true });
    expect(screen.getByRole("button", { name: "Stop generating" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send message" })).not.toBeInTheDocument();
  });

  it("calls onStop when the stop control is pressed", async () => {
    const user = userEvent.setup();
    const { onStop } = setup({ value: "hi", busy: true });
    await user.click(screen.getByRole("button", { name: "Stop generating" }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("cancels with Escape while busy, without destroying the draft", async () => {
    const user = userEvent.setup();
    const { onStop, onChange } = setup({ value: "half typed question", busy: true });
    await user.type(screen.getByLabelText("Message KALIX"), "{Escape}");
    expect(onStop).toHaveBeenCalledTimes(1);
    expect(onChange).not.toHaveBeenCalledWith("");
  });

  it("does not swallow Escape when idle, so the dialog can still close", async () => {
    const user = userEvent.setup();
    const { onStop } = setup({ value: "half typed question", busy: false });
    await user.type(screen.getByLabelText("Message KALIX"), "{Escape}");
    expect(onStop).not.toHaveBeenCalled();
  });

  it("clears the draft from the reset control", async () => {
    const user = userEvent.setup();
    const { onChange } = setup({ value: "draft" });
    await user.click(screen.getByRole("button", { name: "Clear draft" }));
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("hides the reset control when there is nothing to reset", () => {
    setup({ value: "" });
    expect(screen.queryByRole("button", { name: "Clear draft" })).not.toBeInTheDocument();
  });

  it("keeps Attach disabled - an air-gapped build cannot accept a file", () => {
    setup({ value: "hi" });
    expect(screen.getByRole("button", { name: /attach/i })).toBeDisabled();
  });

  it("blocks submission entirely when disabled", async () => {
    const user = userEvent.setup();
    const { onSubmit, box } = setup({ value: "hi", disabled: true });
    await user.type(box, "{Enter}");
    await waitFor(() => expect(onSubmit).not.toHaveBeenCalled());
  });

  it("renders the disclosure footer passed by the screen", () => {
    setup({ footer: <p>Not legal advice.</p> });
    expect(screen.getByText("Not legal advice.")).toBeInTheDocument();
  });

  it("resizes the textarea to fit content, then clamps", async () => {
    const { box } = setup({ value: "one line" });
    // jsdom reports scrollHeight 0, so the clamp floor is what is observable.
    await waitFor(() => expect((box as HTMLTextAreaElement).style.height).toBe("24px"));
  });
});