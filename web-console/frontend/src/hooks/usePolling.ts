import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "../i18n/zh-CN";

type PollingState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  lastUpdatedAt: Date | null;
  refresh: () => void;
};

export function usePolling<T>(
  enabled: boolean,
  intervalMs: number,
  fetcher: (signal: AbortSignal) => Promise<T>,
): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const inFlight = useRef<AbortController | null>(null);
  const timeoutRef = useRef<number | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const clearTimer = () => {
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const run = useCallback(async () => {
    if (!enabled || inFlight.current) return;
    const controller = new AbortController();
    inFlight.current = controller;
    setLoading(true);
    try {
      const nextData = await fetcherRef.current(controller.signal);
      setData(nextData);
      setError(null);
      setLastUpdatedAt(new Date());
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(apiErrorMessage(caught));
      }
    } finally {
      if (inFlight.current === controller) {
        inFlight.current = null;
      }
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      clearTimer();
      inFlight.current?.abort();
      inFlight.current = null;
      return;
    }

    let stopped = false;
    const schedule = () => {
      clearTimer();
      if (!stopped && document.visibilityState === "visible") {
        timeoutRef.current = window.setTimeout(async () => {
          await run();
          schedule();
        }, intervalMs);
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void run();
        schedule();
      } else {
        clearTimer();
      }
    };

    void run();
    schedule();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stopped = true;
      document.removeEventListener("visibilitychange", onVisibility);
      clearTimer();
      inFlight.current?.abort();
      inFlight.current = null;
    };
  }, [enabled, intervalMs, run]);

  return { data, error, loading, lastUpdatedAt, refresh: run };
}
