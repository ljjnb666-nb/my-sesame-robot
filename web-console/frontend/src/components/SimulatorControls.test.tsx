import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SimulatorControls } from "./SimulatorControls";

describe("SimulatorControls", () => {
  it("injects a fault and clears all", async () => {
    const user = userEvent.setup();
    const onInject = vi.fn().mockResolvedValue(undefined);
    const onClearAll = vi.fn().mockResolvedValue(undefined);
    render(
      <SimulatorControls disabled={false} faults={[]} onInject={onInject} onClear={vi.fn()} onClearAll={onClearAll} onResetSimulator={vi.fn()} onResetSession={vi.fn()} />,
    );
    await user.type(screen.getByLabelText("模拟故障注入"), "battery_low");
    await user.click(screen.getByRole("button", { name: "注入故障" }));
    expect(onInject).toHaveBeenCalledWith("battery_low");
    await user.click(screen.getByRole("button", { name: "清除全部故障" }));
    expect(onClearAll).toHaveBeenCalledOnce();
  });

  it("disables controls offline", () => {
    render(<SimulatorControls disabled={true} faults={[]} onInject={vi.fn()} onClear={vi.fn()} onClearAll={vi.fn()} onResetSimulator={vi.fn()} onResetSession={vi.fn()} />);
    expect(screen.getByRole("button", { name: "注入故障" })).toBeDisabled();
  });

  it("uses zh-CN reset confirmation prompts", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const onResetSimulator = vi.fn().mockResolvedValue(undefined);
    const onResetSession = vi.fn().mockResolvedValue(undefined);
    render(
      <SimulatorControls
        disabled={false}
        faults={[]}
        onInject={vi.fn()}
        onClear={vi.fn()}
        onClearAll={vi.fn()}
        onResetSimulator={onResetSimulator}
        onResetSession={onResetSession}
      />,
    );
    await user.click(screen.getByRole("button", { name: "重置模拟器" }));
    expect(confirmSpy.mock.calls[0]?.[0]).toContain("确定要重置模拟器吗");
    await user.click(screen.getByRole("button", { name: "重置会话" }));
    expect(confirmSpy.mock.calls[1]?.[0]).toContain("确定要重置当前会话吗");
    expect(onResetSimulator).toHaveBeenCalledOnce();
    expect(onResetSession).toHaveBeenCalledOnce();
    confirmSpy.mockRestore();
  });
});
