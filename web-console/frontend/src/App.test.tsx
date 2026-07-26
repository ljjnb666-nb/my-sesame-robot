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

const confirmationResponse = {
  status: "confirmation_required",
  action: "walk_forward",
  requiresConfirmation: true,
  confirmationId: "secret-id",
  confirmationFingerprint: "fp",
};

async function openConfirmation(user: ReturnType<typeof userEvent.setup>) {
  apiMock.chat.mockResolvedValueOnce(confirmationResponse);
  render(<App />);
  await screen.findByText("API ONLINE");
  await user.type(screen.getByLabelText(/AI/), "walk forward");
  await user.click(screen.getByRole("button", { name: /send/i }));
  await screen.findByRole("dialog");
}

describe("App confirmation safety", () => {
  beforeEach(() => {
    Object.values(apiMock).forEach((mock) => mock.mockReset());
    apiMock.health.mockResolvedValue({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock" });
    apiMock.state.mockResolvedValue(state);
    apiMock.timeline.mockResolvedValue({ events: [], limit: 20 });
    apiMock.injectFault.mockResolvedValue({ status: "ok", fault: "battery_low", state });
    apiMock.clearFault.mockResolvedValue({ status: "ok", fault: "all", state });
    apiMock.resetSimulator.mockResolvedValue({ status: "ok", generation: 2, state });
    apiMock.resetSession.mockResolvedValue({ status: "ok", sessionId: "s", runtimeConfirmationsRevoked: false });
  });

  it("clears confirmation id after success", async () => {
    const user = userEvent.setup();
    apiMock.chat
      .mockResolvedValueOnce(confirmationResponse)
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

  it("clears confirmation id after stale confirmation explicit failure", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockRejectedValueOnce(new ApiError("stale_confirmation", "confirmation text mismatch", { status: 400 }));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await screen.findByText("confirmation text mismatch");
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("treats invalid_request 400 as explicit failure", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockRejectedValueOnce(new ApiError("invalid_request", "invalid request", { status: 400 }));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await screen.findByText("invalid request");
    expect(screen.queryByText(/未收到最终结果/)).toBeNull();
  });

  it.each([
    ["timeout", new ApiError("timeout", "timeout")],
    ["HTTP 500 internal_error", new ApiError("internal_error", "server failed", { status: 500 })],
    ["HTTP 502 api_error", new ApiError("api_error", "bad gateway", { status: 502 })],
    ["invalid_response", new ApiError("invalid_response", "malformed response")],
    ["plain Error", new Error("connection interrupted")],
  ])("shows outcome unknown for %s after submitted confirmation", async (_name, failure) => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockRejectedValueOnce(failure);
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await screen.findAllByText(/未收到最终结果/);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(apiMock.chat).toHaveBeenCalledTimes(2);
    expect(document.body.textContent ?? "").not.toContain("secret-id");
    expect(document.body.textContent ?? "").not.toContain("动作未执行");
    expect(document.body.textContent ?? "").not.toContain("确认已取消");
  });

  it("cancel clears confirmation id and does not call backend again", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(apiMock.chat).toHaveBeenCalledTimes(1);
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("does not write confirmation id to storage or URL", async () => {
    const user = userEvent.setup();
    const localSpy = vi.spyOn(Storage.prototype, "setItem");
    await openConfirmation(user);
    expect(localSpy).not.toHaveBeenCalled();
    expect(location.href).not.toContain("secret-id");
    localSpy.mockRestore();
  });

  it("sets background inert while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    const background = screen.getByTestId("app-background") as HTMLElement & { inert?: boolean };
    expect(background.inert).toBe(true);
    expect(background).toHaveAttribute("aria-hidden", "true");
  });

  it("removes background inert when dialog closes", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    const background = screen.getByTestId("app-background") as HTMLElement & { inert?: boolean };
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    await waitFor(() => expect(background.inert).toBe(false));
    expect(background).not.toHaveAttribute("aria-hidden");
  });

  it("disables Clear chat while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: /clear chat/i, hidden: true })).toBeDisabled();
  });

  it("disables fault and reset controls while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: /inject/i, hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: /clear all faults/i, hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: /reset simulator/i, hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: /reset session/i, hidden: true })).toBeDisabled();
  });

  it("disables timeline controls while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: /refresh/i, hidden: true })).toBeDisabled();
    expect(document.querySelector("#timeline-limit")).toBeDisabled();
  });

  it("does not cancel with Escape while submitting", async () => {
    const user = userEvent.setup();
    let resolveConfirm: (value: unknown) => void = () => undefined;
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockReturnValueOnce(new Promise((resolve) => { resolveConfirm = resolve; }));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    resolveConfirm({ status: "ok", message: "done", structured: { runtime: { confirmation: { state: "accepted" } } } });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("does not confirm again with Enter while submitting", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockReturnValueOnce(new Promise(() => undefined));
    render(<App />);
    await screen.findByText("API ONLINE");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: /confirm action/i }));
    await user.keyboard("{Enter}");
    expect(apiMock.chat).toHaveBeenCalledTimes(2);
  });
});
