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
    await user.type(screen.getByLabelText(/fault injection/i), "battery_low");
    await user.click(screen.getByRole("button", { name: /inject/i }));
    expect(onInject).toHaveBeenCalledWith("battery_low");
    await user.click(screen.getByRole("button", { name: /clear all faults/i }));
    expect(onClearAll).toHaveBeenCalledOnce();
  });

  it("disables controls offline", () => {
    render(<SimulatorControls disabled={true} faults={[]} onInject={vi.fn()} onClear={vi.fn()} onClearAll={vi.fn()} onResetSimulator={vi.fn()} onResetSession={vi.fn()} />);
    expect(screen.getByRole("button", { name: /inject/i })).toBeDisabled();
  });
});
