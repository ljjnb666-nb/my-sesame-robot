import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../api/client";
import { ApiError, HealthResponse } from "../api/types";

export type ApiHealthStatus = "connecting" | "online" | "offline" | "blocked";

export function useApiHealth() {
  const [status, setStatus] = useState<ApiHealthStatus>("connecting");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const controller = new AbortController();
    setStatus("connecting");
    try {
      const next = await apiClient.health({ signal: controller.signal });
      setHealth(next);
      setError(null);
      setStatus("online");
    } catch (caught) {
      setHealth(null);
      setError(caught instanceof Error ? caught.message : "无法连接本地模拟器 API。");
      setStatus(caught instanceof ApiError && caught.code === "unsafe_mode" ? "blocked" : "offline");
    }
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void apiClient
      .health({ signal: controller.signal })
      .then((next) => {
        setHealth(next);
        setError(null);
        setStatus("online");
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setHealth(null);
        setError(caught instanceof Error ? caught.message : "无法连接本地模拟器 API。");
        setStatus(caught instanceof ApiError && caught.code === "unsafe_mode" ? "blocked" : "offline");
      });
    return () => controller.abort();
  }, []);

  return { status, health, error, refresh };
}
