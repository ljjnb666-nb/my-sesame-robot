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
  motionState: "moving",
  currentCommand: "wave",
  currentFace: "default",
  emergencyStopActive: false,
  communicationTimedOut: false,
  batteryPercent: 80,
  robotPose: "standing",
  chargingState: "not_charging",
  faults: ["battery_low"],
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
  await screen.findByText("接口在线");
  await user.type(screen.getByLabelText(/AI/), "walk forward");
  await user.click(screen.getByRole("button", { name: "发送" }));
  await screen.findByRole("dialog");
}

describe("App confirmation safety and zh-CN UI", () => {
  beforeEach(() => {
    Object.values(apiMock).forEach((mock) => mock.mockReset());
    apiMock.health.mockResolvedValue({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock" });
    apiMock.state.mockResolvedValue(state);
    apiMock.timeline.mockResolvedValue({ events: [], limit: 20 });
    apiMock.injectFault.mockResolvedValue({ status: "ok", fault: "battery_low", state });
    apiMock.clearFault.mockResolvedValue({ status: "ok", fault: "all", state: { ...state, faults: [] } });
    apiMock.resetSimulator.mockResolvedValue({ status: "ok", generation: 2, state: { ...state, faults: [] } });
    apiMock.resetSession.mockResolvedValue({ status: "ok", sessionId: "s", runtimeConfirmationsRevoked: false });
  });

  it("renders zh-CN dashboard labels and robot state mappings", async () => {
    render(<App />);
    await screen.findByText("芝麻机器人模拟器");
    expect(screen.getByText("接口在线")).toBeInTheDocument();
    expect(screen.getByText("AI 对话")).toBeInTheDocument();
    expect(screen.getByText("机器人状态")).toBeInTheDocument();
    expect(screen.getByText("模拟器控制")).toBeInTheDocument();
    expect(screen.getAllByText("运行记录").length).toBeGreaterThan(0);
    expect((await screen.findAllByText("运动中")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("挥手").length).toBeGreaterThan(0);
    expect(screen.getByText("未充电")).toBeInTheDocument();
    expect(screen.getByText("电量过低（battery_low）")).toBeInTheDocument();
  });

  it("clears confirmation id after success and localizes accepted result", async () => {
    const user = userEvent.setup();
    apiMock.chat
      .mockResolvedValueOnce(confirmationResponse)
      .mockResolvedValueOnce({ status: "ok", message: "done", structured: { runtime: { confirmation: { state: "accepted" } } } });
    render(<App />);
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(screen.getAllByText("确认结果：已确认并执行").length).toBeGreaterThan(0);
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("clears confirmation id after stale confirmation explicit failure", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockRejectedValueOnce(new ApiError("stale_confirmation", "confirmation text mismatch", { status: 400 }));
    render(<App />);
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
    await screen.findByText("当前确认内容已失效。");
    expect(document.body.textContent ?? "").not.toContain("secret-id");
  });

  it("treats invalid_request 400 as explicit failure", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockRejectedValueOnce(new ApiError("invalid_request", "invalid request", { status: 400 }));
    render(<App />);
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
    await screen.findByText("请求参数不正确。");
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
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
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
    await user.click(screen.getByRole("button", { name: "取消" }));
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
    await user.click(screen.getByRole("button", { name: "取消" }));
    await waitFor(() => expect(background.inert).toBe(false));
    expect(background).not.toHaveAttribute("aria-hidden");
  });

  it("disables clear chat while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: "清空对话", hidden: true })).toBeDisabled();
  });

  it("disables fault and reset controls while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: "注入故障", hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: "清除全部故障", hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: "重置模拟器", hidden: true })).toBeDisabled();
    expect(screen.getByRole("button", { name: "重置会话", hidden: true })).toBeDisabled();
  });

  it("disables timeline controls while dialog is open", async () => {
    const user = userEvent.setup();
    await openConfirmation(user);
    expect(screen.getByRole("button", { name: "刷新", hidden: true })).toBeDisabled();
    expect(document.querySelector("#timeline-limit")).toBeDisabled();
  });

  it("does not cancel with Escape while submitting", async () => {
    const user = userEvent.setup();
    let resolveConfirm: (value: unknown) => void = () => undefined;
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockReturnValueOnce(new Promise((resolve) => { resolveConfirm = resolve; }));
    render(<App />);
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    resolveConfirm({ status: "ok", message: "done", structured: { runtime: { confirmation: { state: "accepted" } } } });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("does not confirm again with Enter while submitting", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce(confirmationResponse).mockReturnValueOnce(new Promise(() => undefined));
    render(<App />);
    await screen.findByText("接口在线");
    await user.type(screen.getByLabelText(/AI/), "walk forward");
    await user.click(screen.getByRole("button", { name: "发送" }));
    await screen.findByRole("dialog");
    await user.click(screen.getByRole("button", { name: "确认执行" }));
    await user.keyboard("{Enter}");
    expect(apiMock.chat).toHaveBeenCalledTimes(2);
  });

  it.each(["none", "null", "unknown", "", null, undefined, false])("hides empty confirmation result %s", async (emptyState) => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce({ status: "ok", action: "wave", structured: { runtime: { confirmation: { state: emptyState } } } });
    render(<App />);
    await screen.findByText("接口在线");
    await user.click(screen.getByRole("button", { name: "挥手" }));
    await screen.findByText("已执行：挥手");
    expect(document.body.textContent ?? "").not.toContain("Confirmation result: none");
    expect(document.body.textContent ?? "").not.toContain("确认结果：无");
  });

  it("maps expired confirmation result to Chinese", async () => {
    const user = userEvent.setup();
    apiMock.chat.mockResolvedValueOnce({ status: "ok", action: "wave", structured: { runtime: { confirmation: { state: "expired" } } } });
    render(<App />);
    await screen.findByText("接口在线");
    await user.click(screen.getByRole("button", { name: "挥手" }));
    expect((await screen.findAllByText("确认结果：确认已过期，请重新发起")).length).toBeGreaterThan(0);
  });
});
