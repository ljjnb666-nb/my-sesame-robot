import { describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { ApiError } from "./types";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), { ...init, headers: { "content-type": "application/json", ...(init.headers ?? {}) } });
}

describe("apiClient", () => {
  it("parses health success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok", version: "0.4", runtimeMode: "simulator", simulatorOnly: true, provider: "mock" })));
    await expect(apiClient.health()).resolves.toMatchObject({ runtimeMode: "simulator", simulatorOnly: true });
  });

  it("blocks unsafe health", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok", version: "0.4", runtimeMode: "real", simulatorOnly: false, provider: "mock" })));
    await expect(apiClient.health()).rejects.toMatchObject({ code: "unsafe_mode" });
  });

  it("handles non-json response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>no</html>", { headers: { "content-type": "text/html" } })));
    await expect(apiClient.health()).rejects.toMatchObject({ code: "invalid_json" });
  });

  it("parses api error envelope without leaking confirmation text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ code: "invalid_request", message: "bad request" }, { status: 400 })));
    await expect(apiClient.chat({ text: "walk", confirmationId: "secret-confirmation-id" })).rejects.toThrow("bad request");
  });

  it("maps offline errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    await expect(apiClient.health()).rejects.toBeInstanceOf(ApiError);
  });
});
