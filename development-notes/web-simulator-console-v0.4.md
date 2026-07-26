# Web Simulator Console v0.4

This PR adds a React/Vite TypeScript local-only simulator console under `web-console/frontend`.

## Install

Python web API:

```powershell
cd ai-controller
python -m pip install -e ".[web]"
```

Frontend:

```powershell
cd web-console/frontend
npm install
```

Run both locally:

```powershell
powershell -ExecutionPolicy Bypass -File .\web-console\run-dev.ps1
```

## Boundaries

The browser only calls existing `/api` endpoints. Chat and quick commands use `POST /api/chat`; the frontend does not construct ToolCalls, action executor requests, servo values, motor values, runtime mode overrides, or real hardware switches.

`confirmationId` is retained only in current React memory for the pending dialog. It is not rendered, logged, placed in DOM data attributes, URL parameters, or browser storage.

During confirmation submission, Cancel, Confirm, Enter, and Escape are disabled until the Runtime returns a final response. If the request times out, aborts, goes offline, or returns invalid JSON after submission, the UI reports the outcome as unknown, clears the in-memory confirmation, refreshes robot state and timeline, and does not retry automatically.

The confirmation dialog isolates focus from the background app. The Header/Main wrapper is marked `inert` and `aria-hidden` while any confirmation dialog is open, and background write controls are disabled, including Chat Send, Quick Commands, Clear chat, Fault inject/clear, Reset simulator, Reset session, and Timeline controls. During submitting, focus is moved to the dialog itself and Tab, Shift+Tab, Space, Escape, and Enter cannot escape the dialog or activate background controls.

## API Integration

Development and preview proxy `/api` to `http://127.0.0.1:8787`. `VITE_API_BASE_URL` can override the base URL at build/dev time without storing credentials in the frontend.

The frontend only accepts `/api`, `http://127.0.0.1:<port>/api`, and `http://localhost:<port>/api`. Absolute loopback URLs must have an exact `/api` path, with `/api/` normalized to `/api`; query strings, fragments, `/foo/api`, `/v1/api`, and `/api/extra` are rejected. Public, LAN, `0.0.0.0`, credentialed URLs, protocol-relative URLs, HTTPS URLs, and non-HTTP schemes are blocked before any network request. `VITE_DEV_API_TARGET` is validated with the same loopback-only rule in Vite proxy configuration.

The client uses `AbortController`, request timeouts, JSON response checks, typed parsers, and a unified `ApiError`.

Nested API error envelopes in the form `{ "error": { "code": "...", "message": "..." } }` are parsed strictly. Known safe codes include `invalid_request`, `stale_confirmation`, `unknown_fault`, `request_too_large`, `not_found`, and `internal_error`; unknown or malformed envelopes fall back to `api_error` without stringifying arbitrary objects. Displayed messages are length-limited and redacted for confirmation IDs, tokens, and local paths.

Timeline event result rendering is allowlisted to `status`, `state`, `code`, `result`, and `reason`. The UI does not enumerate unknown result keys and does not stringify full backend objects.

Health reconnects abort previous probes, ignore stale generations, and abort on unmount.

Playwright trace, HAR, video, automatic screenshots, network archives, and request-body dumps are disabled for confirmation E2E because confirmation request bodies contain the in-memory confirmation token. CI checks generated browser artifacts and fails if trace/HAR/video/network/request-body files are present.

## Hardware

Real hardware remains disabled. No serial port, ESP32 upload, camera, microphone, servo, motor, battery, or charging dock access is performed.
