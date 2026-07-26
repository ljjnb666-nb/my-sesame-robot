import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { usePolling } from "./usePolling";

describe("usePolling", () => {
  it("polls and aborts on unmount", async () => {
    const fetcher = vi.fn(async (signal: AbortSignal) => (signal.aborted ? "aborted" : "ok"));
    const { result, unmount } = renderHook(() => usePolling(true, 1000, fetcher));
    await waitFor(() => expect(result.current.data).toBe("ok"));
    unmount();
    expect(fetcher).toHaveBeenCalled();
  });
});
