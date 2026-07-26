import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/types";
import { useApiHealth } from "./useApiHealth";

const healthMock = vi.hoisted(() => vi.fn());

vi.mock("../api/client", () => ({
  apiClient: {
    health: healthMock,
  },
}));

describe("useApiHealth", () => {
  beforeEach(() => {
    healthMock.mockReset();
  });

  it("goes online on simulator health", async () => {
    healthMock.mockResolvedValue({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock" });
    const { result } = renderHook(() => useApiHealth());
    await waitFor(() => expect(result.current.status).toBe("online"));
  });

  it("goes blocked on unsafe mode", async () => {
    healthMock.mockRejectedValue(new ApiError("unsafe_mode", "unsafe"));
    const { result } = renderHook(() => useApiHealth());
    await waitFor(() => expect(result.current.status).toBe("blocked"));
  });

  it("goes blocked on invalid api base", async () => {
    healthMock.mockRejectedValue(new ApiError("invalid_api_base", "bad base"));
    const { result } = renderHook(() => useApiHealth());
    await waitFor(() => expect(result.current.status).toBe("blocked"));
  });

  it("goes offline on connection failure", async () => {
    healthMock.mockRejectedValue(new ApiError("offline", "offline"));
    const { result } = renderHook(() => useApiHealth());
    await waitFor(() => expect(result.current.status).toBe("offline"));
  });

  it("aborts previous reconnect", async () => {
    const signals: AbortSignal[] = [];
    healthMock.mockImplementation(({ signal }: { signal: AbortSignal }) => {
      signals.push(signal);
      return new Promise(() => undefined);
    });
    const { result } = renderHook(() => useApiHealth());
    act(() => {
      void result.current.refresh();
    });
    expect(signals[0].aborted).toBe(true);
  });

  it("ignores stale earlier response", async () => {
    let resolveFirst: (value: unknown) => void = () => undefined;
    healthMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
      .mockResolvedValueOnce({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock2" });
    const { result } = renderHook(() => useApiHealth());
    act(() => {
      void result.current.refresh();
    });
    resolveFirst({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "old" });
    await waitFor(() => expect(result.current.health?.provider).toBe("mock2"));
  });

  it("aborts on unmount", () => {
    const signals: AbortSignal[] = [];
    healthMock.mockImplementation(({ signal }: { signal: AbortSignal }) => {
      signals.push(signal);
      return new Promise(() => undefined);
    });
    const { unmount } = renderHook(() => useApiHealth());
    unmount();
    expect(signals[0].aborted).toBe(true);
  });
});
