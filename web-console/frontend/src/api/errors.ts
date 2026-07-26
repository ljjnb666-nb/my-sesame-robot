import { ApiError } from "./types";

export function toUserError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.name === "AbortError") {
    return "请求已取消。";
  }
  return "请求失败。";
}

export function redactSensitiveText(value: string): string {
  return value
    .replace(/confirmationId["']?\s*[:=]\s*["']?[^"',\s}]+/gi, "confirmationId=[hidden]")
    .replace(/confirmation_id["']?\s*[:=]\s*["']?[^"',\s}]+/gi, "confirmation_id=[hidden]")
    .replace(/[a-f0-9]{24,}/gi, "[hidden-id]")
    .replace(/sk-[A-Za-z0-9_-]+/g, "[hidden-key]")
    .replace(/[A-Za-z]:\\[^\s]+/g, "[hidden-path]")
    .replace(/\/(?:Users|home|tmp)\/[^\s]+/g, "[hidden-path]");
}
