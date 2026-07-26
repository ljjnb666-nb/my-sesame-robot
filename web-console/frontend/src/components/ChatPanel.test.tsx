import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

describe("ChatPanel", () => {
  it("sends with Enter and keeps Shift+Enter as newline", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    const onInput = vi.fn();
    render(<ChatPanel messages={[]} input="hello" disabled={false} sending={false} onInput={onInput} onSend={onSend} onClear={vi.fn()} />);
    await user.click(screen.getByLabelText("AI 指令"));
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledOnce();
  });

  it("does not expose dangerouslySetInnerHTML behavior", () => {
    const container = render(
      <ChatPanel
        messages={[{ id: "1", role: "assistant", text: "<img src=x onerror=alert(1)>", createdAt: new Date() }]}
        input=""
        disabled={false}
        sending={false}
        onInput={vi.fn()}
        onSend={vi.fn()}
        onClear={vi.fn()}
      />,
    ).container;
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
  });

  it("disables empty submit", () => {
    render(<ChatPanel messages={[]} input="" disabled={false} sending={false} onInput={vi.fn()} onSend={vi.fn()} onClear={vi.fn()} />);
    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });
});
