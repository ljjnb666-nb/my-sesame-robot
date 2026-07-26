import { ApiError } from "./types";

export type ApiBaseResult =
  | { ok: true; base: string }
  | { ok: false; error: ApiError };

const INVALID_API_BASE = "API base must be /api or an HTTP loopback /api URL.";

function isAllowedHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function invalidApiBase(): ApiBaseResult {
  return { ok: false, error: new ApiError("invalid_api_base", INVALID_API_BASE) };
}

export function validateApiBase(value: string | undefined): ApiBaseResult {
  const raw = (value ?? "/api").trim();
  if (raw === "/api") return { ok: true, base: raw };
  if (raw.startsWith("//")) return invalidApiBase();

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return invalidApiBase();
  }

  const path = parsed.pathname.replace(/\/$/, "");
  if (
    parsed.protocol !== "http:" ||
    !isAllowedHost(parsed.hostname) ||
    Boolean(parsed.username || parsed.password) ||
    !path.endsWith("/api")
  ) {
    return invalidApiBase();
  }
  return { ok: true, base: raw.replace(/\/$/, "") };
}
