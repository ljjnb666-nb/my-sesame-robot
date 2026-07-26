import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../api/client";
import { ApiError, HealthResponse } from "../api/types";
import { apiErrorMessage } from "../i18n/zh-CN";

export type ApiHealthStatus = "connecting" | "online" | "offline" | "blocked";

function statusFromError(error: unknown): ApiHealthStatus {
  return error instanceof ApiError && (error.code === "unsafe_mode" || error.code === "invalid_api_base") ? "blocked" : "offline";
}

export function useApiHealth() {
  const [status, setStatus] = useState<ApiHealthStatus>("connecting");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const generationRef = useRef(0);

  const refresh = useCallback(async () => {
    controllerRef.current?.abort();
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    const controller = new AbortController();
    controllerRef.current = controller;
    setStatus("connecting");
    try {
      const next = await apiClient.health({ signal: controller.signal });
      if (generationRef.current !== generation || controller.signal.aborted) return;
      setHealth(next);
      setError(null);
      setStatus("online");
    } catch (caught) {
      if (generationRef.current !== generation || controller.signal.aborted) return;
      setHealth(null);
      setError(apiErrorMessage(caught));
      setStatus(statusFromError(caught));
    }
  }, []);

  useEffect(() => {
    void refresh();
    return () => {
      generationRef.current += 1;
      controllerRef.current?.abort();
      controllerRef.current = null;
    };
  }, [refresh]);

  return { status, health, error, refresh };
}
