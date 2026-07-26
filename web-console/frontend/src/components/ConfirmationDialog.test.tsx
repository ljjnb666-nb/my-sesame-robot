import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmationDialog } from "./ConfirmationDialog";

const pending = {
  originalText: "walk",
  confirmationId: "full-secret-confirmation-id-should-not-render",
  action: "walk_forward",
  fingerprint: "fp-123",
  message: "Needs confirmation",
};

describe("ConfirmationDialog", () => {
  it("renders fingerprint but not confirmation id", () => {
    render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("fp-123")).toBeInTheDocument();
    expect(screen.queryByText(pending.confirmationId)).toBeNull();
  });

  it("focuses cancel when opened idle", () => {
    render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: "取消" })).toHaveFocus();
  });

  it("Enter does not confirm and Escape cancels while idle", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={onConfirm} onCancel={onCancel} />);
    await user.keyboard("{Enter}");
    expect(onConfirm).not.toHaveBeenCalled();
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("confirm button is not autofocus", () => {
    render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: "确认执行" })).not.toHaveFocus();
  });

  it("does not restore opener focus when idle changes to submitting", () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const { rerender } = render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    rerender(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(opener).not.toHaveFocus();
    expect(screen.getByRole("dialog")).toHaveFocus();
    opener.remove();
  });

  it("focuses dialog itself while submitting", () => {
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  it("keeps Tab focus on dialog when all buttons are disabled", async () => {
    const user = userEvent.setup();
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    await user.keyboard("{Tab}");
    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  it("keeps Shift+Tab focus on dialog when all buttons are disabled", async () => {
    const user = userEvent.setup();
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("dialog")).toHaveFocus();
  });

  it("cycles Tab within idle dialog buttons", async () => {
    const user = userEvent.setup();
    render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(screen.getByRole("button", { name: "确认执行" })).toHaveFocus();
    await user.keyboard("{Tab}");
    expect(screen.getByRole("button", { name: "取消" })).toHaveFocus();
  });

  it("does not cancel with Escape while submitting", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={onCancel} />);
    await user.keyboard("{Escape}");
    expect(onCancel).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("disables both buttons while submitting", () => {
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: "取消" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "确认执行" })).toBeDisabled();
  });

  it("does not confirm with Enter while submitting", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={onConfirm} onCancel={vi.fn()} />);
    await user.keyboard("{Enter}");
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("does not activate confirmation controls with Space while submitting", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={onConfirm} onCancel={onCancel} />);
    await user.keyboard(" ");
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("restores opener focus only after dialog closes", () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const { rerender } = render(<ConfirmationDialog confirmation={pending} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(opener).not.toHaveFocus();
    rerender(<ConfirmationDialog confirmation={null} mode="idle" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(opener).toHaveFocus();
    opener.remove();
  });

  it("shows runtime wait text while submitting", () => {
    render(<ConfirmationDialog confirmation={pending} mode="submitting" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText(/正在等待机器人运行系统返回最终结果/)).toBeInTheDocument();
  });
});
