import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api/types";
import { App } from "./App";

const apiMock = vi.hoisted(() => ({
  health: vi.fn(),
  state: vi.fn(),
  timeline: vi.fn(),
  chat: vi.fn(),
  injectFault: vi.fn(),
  clearFault: vi.fn(),
  resetSimulator: vi.fn(),
  resetSession: vi.fn(),
}));

vi.mock("./api/client", () => ({ apiClient: apiMock }));

const state = {
  runtimeMode: "simulator",
  motionState: "idle",
  currentCommand: "",
  currentFace: "default",
  emergencyStopActive: false,
  communicationTimedOut: false,
  batteryPercent: 80,
  robotPose: "standing",
  chargingState: "not_charging",
  faults: [],
};

describe("App confirmation safety", () => {
  beforeEach(() => {
    Object.values(apiMock).forEach((mock) => mock.mockReset());
    apiMock.health.mockResolvedValue({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock" });
    apiMock.state.mockResolvedValue(state);
    apiMock.timeline.mockResolvedValue({ events: [], limit: 20 });
  });

  it("clears confirmation id after success", async () => {
    const user = userEvent.setup();
    apiMock.chat
      .mockResolvedValueOnce({ status: "confirmation_required", action: "walk_forward", requiresConfirmation: true, confirmationId: "secret-id", confirmationFingerprint: "fp" })
      .mockResolvedValueOnce({ status: "ok", message: "done", structured: { runtime: { confirmation: { state: "accepted" } } } });
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("clears confirmation id after explicit failure", async () => {
    const user = userEvent.setup();
    apiMock.chat
      .mockResolvedValueOnce({ status: "confirmation_required", action: "walk_forward", requiresConfirmation: true, confirmationId: "secret-id", confirmationFingerprint: "fp" })
      .mockRejectedValueOnce(new ApiError("stale_confirmation", "confirmation text mismatch"));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await screen.findByText("confirmation text mismatch");
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("shows outcome unknown on confirmation timeout", async () => {
    const user = userEvent.setup();
    apiMock.chat
      .mockResolvedValueOnce({ status: "confirmation_required", action: "walk_forward", requiresConfirmation: true, confirmationId: "secret-id", confirmationFingerprint: "fp" })
      .mockRejectedValueOnce(new ApiError("timeout", "timeout"));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await waitFor(() => expect(screen.getAllByText(/未收到最终结果/).length).toBeGreaterThan(0));
    expect(document.body.textContent ?? "").not.toContain("动作未执行");
  });

  it("cancel clears confirmation id and does not call backend again", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce({ status: "confirmation_required", action: "walk_forward", requiresConfirmation: true, confirmationId: "secret-id", confirmationFingerprint: "fp" });
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(apiMock.chat).toHaveBeenCalledTimes(1);
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("does not write confirmation id to storage or URL", async () => {
    const user = userEvent.setup();
    const localSpy = vi.spyOn(Storage.prototype, "setItem");
    apiMock.chat.mockResolvedValueOnce({ status: "confirmation_required", action: "walk_forward", requiresConfirmation: true, confirmationId: "secret-id", confirmationFingerprint: "fp" });
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    expect(localSpy).not.toHaveBeenCalled();
    expect(location.href).not.toContain("secret-id");
    localSpy.mockRestore();
  });
});
