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

## API Integration

Development and preview proxy `/api` to `http://127.0.0.1:8787`. `VITE_API_BASE_URL` can override the base URL at build/dev time without storing credentials in the frontend.

The client uses `AbortController`, request timeouts, JSON response checks, typed parsers, and a unified `ApiError`.

## Hardware

Real hardware remains disabled. No serial port, ESP32 upload, camera, microphone, servo, motor, battery, or charging dock access is performed.
