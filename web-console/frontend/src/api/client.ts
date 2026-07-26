import {
  ApiError,
  ChatRequest,
  ChatResponse,
  FaultResponse,
  HealthResponse,
  RobotStateResponse,
  SessionResetResponse,
  SimulatorResetResponse,
  TimelineEvent,
  TimelineResponse,
} from "./types";
import { validateApiBase } from "./base";
import { redactSensitiveText } from "./errors";

const DEFAULT_TIMEOUT_MS = 8_000;
const apiBaseResult = validateApiBase(import.meta.env.VITE_API_BASE_URL as string | undefined);
const apiBase = apiBaseResult.ok ? apiBaseResult.base : "/api";
const ERROR_MESSAGE_LIMIT = 240;
const ERROR_CODE_LIMIT = 64;
const KNOWN_API_CODES = new Set([
  "invalid_request",
  "stale_confirmation",
  "unknown_fault",
  "request_too_large",
  "not_found",
  "internal_error",
]);

type RequestOptions = {
  signal?: AbortSignal;
  timeoutMs?: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringField(record: Record<string, unknown>, key: string, fallback = ""): string {
  return typeof record[key] === "string" ? record[key] : fallback;
}

function nullableString(record: Record<string, unknown>, key: string): string | null {
  return typeof record[key] === "string" ? record[key] : null;
}

function booleanField(record: Record<string, unknown>, key: string): boolean | null {
  return typeof record[key] === "boolean" ? record[key] : null;
}

function numberField(record: Record<string, unknown>, key: string): number | null {
  return typeof record[key] === "number" && Number.isFinite(record[key]) ? record[key] : null;
}

function stringsField(record: Record<string, unknown>, key: string): string[] {
  return Array.isArray(record[key]) ? record[key].filter((item): item is string => typeof item === "string") : [];
}

function clippedSafeMessage(value: string): string {
  return redactSensitiveText(value).slice(0, ERROR_MESSAGE_LIMIT);
}

function parseApiError(payload: unknown, status: number): ApiError {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return new ApiError("api_error", "API 请求失败。", { status });
  }
  const rawCode = payload.error.code;
  const code = typeof rawCode === "string" && rawCode.length <= ERROR_CODE_LIMIT && KNOWN_API_CODES.has(rawCode) ? rawCode : "api_error";
  const message = typeof payload.error.message === "string" ? clippedSafeMessage(payload.error.message) : "API 请求失败。";
  return new ApiError(code as ApiError["code"], message, { status });
}

function joinSignals(external: AbortSignal | undefined, timeoutMs: number): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(new DOMException("Timeout", "TimeoutError")), timeoutMs);
  const onAbort = () => controller.abort(external?.reason);
  if (external) {
    if (external.aborted) onAbort();
    else external.addEventListener("abort", onAbort, { once: true });
  }
  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timer);
      external?.removeEventListener("abort", onAbort);
    },
  };
}

async function requestJson(path: string, init: RequestInit = {}, options: RequestOptions = {}): Promise<unknown> {
  if (!apiBaseResult.ok) throw apiBaseResult.error;
  const { signal, cleanup } = joinSignals(options.signal, options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
  try {
    const response = await fetch(`${apiBase}${path}`, {
      ...init,
      signal,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.includes("application/json")) {
      throw new ApiError("invalid_json", "后端返回了非 JSON 响应。", { status: response.status });
    }
    const payload: unknown = await response.json();
    if (!response.ok) {
      throw parseApiError(payload, response.status);
    }
    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("abort", "请求已取消。");
    }
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new ApiError("timeout", "请求超时。");
    }
    if (signal.aborted) {
      throw new ApiError("timeout", "请求超时。");
    }
    throw new ApiError("offline", "无法连接本地模拟器 API。");
  } finally {
    cleanup();
  }
}

function parseHealth(payload: unknown): HealthResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Health 响应格式无效。");
  const parsed: HealthResponse = {
    status: stringField(payload, "status"),
    version: stringField(payload, "version"),
    runtimeMode: stringField(payload, "runtimeMode"),
    simulatorOnly: payload.simulatorOnly === true,
    provider: stringField(payload, "provider"),
  };
  if (parsed.runtimeMode !== "simulator" || parsed.simulatorOnly !== true) {
    throw new ApiError("unsafe_mode", "当前后端不是安全模拟器模式。");
  }
  return parsed;
}

export function parseRobotState(payload: unknown): RobotStateResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "State 响应格式无效。");
  return {
    runtimeMode: stringField(payload, "runtimeMode"),
    motionState: nullableString(payload, "motionState"),
    currentCommand: nullableString(payload, "currentCommand"),
    currentFace: nullableString(payload, "currentFace"),
    emergencyStopActive: booleanField(payload, "emergencyStopActive"),
    communicationTimedOut: booleanField(payload, "communicationTimedOut"),
    batteryPercent: numberField(payload, "batteryPercent"),
    robotPose: nullableString(payload, "robotPose"),
    chargingState: nullableString(payload, "chargingState"),
    faults: stringsField(payload, "faults"),
  };
}

function parseTimelineEvent(value: unknown): TimelineEvent | null {
  if (!isRecord(value)) return null;
  const result = isRecord(value.result) ? value.result : {};
  return {
    time: nullableString(value, "time") ?? nullableString(value, "createdAt") ?? undefined,
    timestamp: nullableString(value, "timestamp") ?? undefined,
    eventType: nullableString(value, "eventType") ?? undefined,
    action: nullableString(value, "action") ?? undefined,
    resultStatus: nullableString(result, "status") ?? undefined,
    resultState: nullableString(result, "state") ?? undefined,
    resultCode: nullableString(result, "code") ?? nullableString(result, "result") ?? undefined,
    resultReason: nullableString(result, "reason") ?? undefined,
    reason: nullableString(value, "reason") ?? undefined,
    safetySeverity: nullableString(value, "safetySeverity") ?? undefined,
    runtimeMode: nullableString(value, "runtimeMode") ?? undefined,
    fault: nullableString(value, "fault") ?? undefined,
  };
}

function parseTimeline(payload: unknown): TimelineResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Timeline 响应格式无效。");
  const events = Array.isArray(payload.events) ? payload.events.map(parseTimelineEvent).filter((event): event is TimelineEvent => event !== null) : [];
  return {
    events,
    limit: numberField(payload, "limit") ?? events.length,
  };
}

function parseChat(payload: unknown): ChatResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Chat 响应格式无效。");
  return {
    status: stringField(payload, "status"),
    message: nullableString(payload, "message") ?? nullableString(payload, "user_message") ?? undefined,
    userMessage: nullableString(payload, "userMessage") ?? undefined,
    action: nullableString(payload, "action"),
    requiresConfirmation: payload.requiresConfirmation === true || payload.status === "confirmation_required",
    confirmationId: nullableString(payload, "confirmationId") ?? undefined,
    confirmationFingerprint: nullableString(payload, "confirmationFingerprint"),
    structured: isRecord(payload.structured) ? payload.structured : undefined,
    reason: nullableString(payload, "reason"),
  };
}

function parseFault(payload: unknown): FaultResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Fault 响应格式无效。");
  return {
    status: stringField(payload, "status"),
    fault: stringField(payload, "fault"),
    state: parseRobotState(payload.state),
  };
}

function parseSimulatorReset(payload: unknown): SimulatorResetResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Simulator reset 响应格式无效。");
  return {
    status: stringField(payload, "status"),
    generation: numberField(payload, "generation") ?? 0,
    state: parseRobotState(payload.state),
  };
}

function parseSessionReset(payload: unknown): SessionResetResponse {
  if (!isRecord(payload)) throw new ApiError("invalid_response", "Session reset 响应格式无效。");
  return {
    status: stringField(payload, "status"),
    sessionId: stringField(payload, "sessionId"),
    runtimeConfirmationsRevoked: payload.runtimeConfirmationsRevoked === true,
  };
}

export const apiClient = {
  async health(options?: RequestOptions): Promise<HealthResponse> {
    return parseHealth(await requestJson("/health", {}, options));
  },
  async state(options?: RequestOptions): Promise<RobotStateResponse> {
    return parseRobotState(await requestJson("/state", {}, options));
  },
  async timeline(limit: number, options?: RequestOptions): Promise<TimelineResponse> {
    return parseTimeline(await requestJson(`/timeline?limit=${encodeURIComponent(String(limit))}`, {}, options));
  },
  async chat(request: ChatRequest, options?: RequestOptions): Promise<ChatResponse> {
    return parseChat(await requestJson("/chat", { method: "POST", body: JSON.stringify(request) }, options));
  },
  async injectFault(fault: string, options?: RequestOptions): Promise<FaultResponse> {
    return parseFault(await requestJson("/simulator/faults", { method: "POST", body: JSON.stringify({ fault }) }, options));
  },
  async clearFault(fault: string, options?: RequestOptions): Promise<FaultResponse> {
    return parseFault(await requestJson(`/simulator/faults/${encodeURIComponent(fault)}`, { method: "DELETE" }, options));
  },
  async resetSimulator(options?: RequestOptions): Promise<SimulatorResetResponse> {
    return parseSimulatorReset(await requestJson("/simulator/reset", { method: "POST", body: JSON.stringify({}) }, options));
  },
  async resetSession(options?: RequestOptions): Promise<SessionResetResponse> {
    return parseSessionReset(await requestJson("/session/reset", { method: "POST", body: JSON.stringify({}) }, options));
  },
};
