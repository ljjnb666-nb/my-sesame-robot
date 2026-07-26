import { describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { ApiError } from "./types";
import { validateApiBase } from "./base";

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
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "invalid_request", message: "bad request" } }, { status: 400 })));
    await expect(apiClient.chat({ text: "walk", confirmationId: "secret-confirmation-id" })).rejects.toThrow("bad request");
  });

  it("maps offline errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("failed")));
    await expect(apiClient.health()).rejects.toBeInstanceOf(ApiError);
  });

  it("parses stale confirmation envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "stale_confirmation", message: "confirmation text mismatch" } }, { status: 400 })));
    await expect(apiClient.chat({ text: "walk", confirmationId: "id" })).rejects.toMatchObject({ code: "stale_confirmation", status: 400 });
  });

  it("parses unknown fault envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "unknown_fault", message: "unknown simulator fault" } }, { status: 404 })));
    await expect(apiClient.injectFault("bad")).rejects.toMatchObject({ code: "unknown_fault", status: 404 });
  });

  it("does not accept flat fake error envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ code: "stale_confirmation", message: "flat" }, { status: 400 })));
    await expect(apiClient.chat({ text: "walk", confirmationId: "id" })).rejects.toMatchObject({ code: "api_error" });
  });

  it("falls back on non-string error code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: 1, message: "bad" } }, { status: 400 })));
    await expect(apiClient.health()).rejects.toMatchObject({ code: "api_error" });
  });

  it("falls back on non-string error message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "invalid_request", message: { html: "<b>x</b>" } } }, { status: 400 })));
    await expect(apiClient.health()).rejects.toThrow("接口请求失败。");
  });

  it("clips long error messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "invalid_request", message: "x".repeat(500) } }, { status: 400 })));
    try {
      await apiClient.health();
      throw new Error("expected failure");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as Error).message.length).toBeLessThanOrEqual(240);
    }
  });

  it("redacts secrets from error messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ error: { code: "invalid_request", message: "sk-secret C:\\Users\\me\\file confirmationId=abcdefabcdefabcdefabcdefabcdefab" } }, { status: 400 })));
    await expect(apiClient.health()).rejects.not.toThrow(/sk-secret|Users|abcdefabcdef/);
  });

  it("normalizes timeline result fields with allowlist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          limit: 20,
          events: [
            {
              eventType: "runtime",
              result: {
                status: "ok",
                state: "accepted",
                code: "done",
                secret: "sk-secret",
                nested: { leak: true },
                array: ["leak"],
              },
            },
          ],
        }),
      ),
    );
    const timeline = await apiClient.timeline(20);
    expect(timeline.events[0]).toMatchObject({ resultStatus: "ok", resultState: "accepted", resultCode: "done" });
    expect(JSON.stringify(timeline)).not.toContain("sk-secret");
    expect(JSON.stringify(timeline)).not.toContain("nested");
  });

  it("rejects malformed chat responses without status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ message: "missing status" })));
    await expect(apiClient.chat({ text: "walk", confirmationId: "id" })).rejects.toMatchObject({ code: "invalid_response" });
  });
});

describe("validateApiBase", () => {
  it.each([
    [undefined],
    ["/api"],
    ["http://127.0.0.1:8787/api"],
    ["http://localhost:8787/api"],
  ])("accepts safe base %s", (value) => {
    expect(validateApiBase(value).ok).toBe(true);
  });

  it("normalizes trailing slash on loopback API base", () => {
    expect(validateApiBase("http://localhost:8787/api/")).toEqual({ ok: true, base: "http://localhost:8787/api" });
  });

  it.each([
    ["https://example.com/api"],
    ["https://localhost:8787/api"],
    ["http://[::1]:8787/api"],
    ["http://localhost:8787/foo/api"],
    ["http://localhost:8787/v1/api"],
    ["http://localhost:8787/api/extra"],
    ["http://localhost:8787/api?x=1"],
    ["http://localhost:8787/api#x"],
    ["http://0.0.0.0:8787/api"],
    ["http://192.168.1.2:8787/api"],
    ["http://user:pass@127.0.0.1:8787/api"],
    ["//example.com/api"],
    ["javascript:alert(1)"],
    ["data:text/plain,api"],
    ["file:///tmp/api"],
  ])("rejects unsafe base %s", (value) => {
    expect(validateApiBase(value).ok).toBe(false);
  });
});
