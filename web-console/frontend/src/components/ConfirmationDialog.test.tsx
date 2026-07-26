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
    render(<ConfirmationDialog confirmation={pending} busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("fp-123")).toBeInTheDocument();
    expect(screen.queryByText(pending.confirmationId)).toBeNull();
  });

  it("Enter does not confirm and Escape cancels", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(<ConfirmationDialog confirmation={pending} busy={false} onConfirm={onConfirm} onCancel={onCancel} />);
    await user.keyboard("{Enter}");
    expect(onConfirm).not.toHaveBeenCalled();
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("confirm button is not autofocus", () => {
    render(<ConfirmationDialog confirmation={pending} busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByRole("button", { name: /confirm action/i })).not.toHaveFocus();
  });
});
