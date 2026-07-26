import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { usePolling } from "./usePolling";

describe("usePolling", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls and aborts on unmount", async () => {
    const fetcher = vi.fn(async (signal: AbortSignal) => (signal.aborted ? "aborted" : "ok"));
    const { result, unmount } = renderHook(() => usePolling(true, 1000, fetcher));
    await waitFor(() => expect(result.current.data).toBe("ok"));
    unmount();
    expect(fetcher).toHaveBeenCalled();
  });

  it("requests immediately and again after interval", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn().mockResolvedValue("ok");
    renderHook(() => usePolling(true, 1000, fetcher));
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("does not overlap in-flight requests", async () => {
    vi.useFakeTimers();
    let resolveFirst: (value: string) => void = () => undefined;
    const fetcher = vi.fn(() => new Promise<string>((resolve) => { resolveFirst = resolve; }));
    renderHook(() => usePolling(true, 1000, fetcher));
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetcher).toHaveBeenCalledTimes(1);
    await act(async () => resolveFirst("ok"));
  });

  it("aborts when disabled", async () => {
    const signals: AbortSignal[] = [];
    const fetcher = vi.fn((signal: AbortSignal) => {
      signals.push(signal);
      return new Promise<string>(() => undefined);
    });
    const { rerender } = renderHook(({ enabled }) => usePolling(enabled, 1000, fetcher), { initialProps: { enabled: true } });
    act(() => {
      rerender({ enabled: false });
    });
    expect(signals[0].aborted).toBe(true);
  });

  it("manual refresh does not duplicate in-flight", async () => {
    const fetcher = vi.fn(() => new Promise<string>(() => undefined));
    const { result } = renderHook(() => usePolling(true, 1000, fetcher));
    await act(async () => {
      void result.current.refresh();
    });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("does not show errors for aborted requests", async () => {
    const fetcher = vi.fn(() => new Promise<string>(() => undefined));
    const { result, unmount } = renderHook(() => usePolling(true, 1000, fetcher));
    act(() => {
      unmount();
    });
    expect(result.current.error).toBeNull();
  });
});
