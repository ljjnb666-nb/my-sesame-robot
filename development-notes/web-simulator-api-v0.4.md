# Web Simulator API v0.4

PR #7a adds a localhost-only backend API for testing the current simulator, AI loop, tool calling, Runtime, Arbiter, confirmation lifecycle, and virtual hardware without real hardware.

## Scope

- Backend API only.
- No React, Vite, or frontend implementation.
- Single user, single process, single worker, single simulator session.
- Local development only; not a production control panel.
- Real hardware remains disabled.

## Safety Chain

Chat and action requests follow:

```text
HTTP Request
-> Web API
-> RobotSimulatorService
-> AIInteractionLoop.handle_text()
-> ToolExecutor
-> RobotRuntime.step()
-> BehaviorArbiter
-> ConfirmationStore
-> VirtualHardwareRobotClient
```

Read-only requests follow:

```text
HTTP Request
-> Web API
-> RobotSimulatorService
-> ToolExecutor
-> RobotReadOnlyFacade
```

Routes do not receive raw hardware, client, Runtime, ToolExecutor, or ConfirmationStore objects.

## Routes

- `GET /api/health`
- `POST /api/chat`
- `GET /api/state`
- `GET /api/timeline?limit=20`
- `POST /api/simulator/faults`
- `DELETE /api/simulator/faults/{fault}`
- `POST /api/simulator/reset`
- `POST /api/session/reset`

## Lifecycle

`RobotSimulatorService` owns the long-lived simulator session. It keeps one AI loop, Runtime, ConfirmationStore, MemoryManager, ToolRegistry, ToolExecutor, read-only facade, simulator hardware adapter, and virtual robot client.

The service uses an in-process `RLock` to avoid reset/chat/fault/session operations interleaving. Multi-worker operation is not supported because it would split Runtime, ConfirmationStore, Memory, and simulator state.

`POST /api/simulator/reset` rebuilds the simulator hardware, virtual client, Runtime, read-only facade, ToolExecutor, and ConfirmationStore. Old confirmation IDs no longer authorize actions.

`POST /api/session/reset` clears the AI conversation session and short-term memory, while preserving simulator hardware and long-term memory.

## Network Boundary

The default host is `127.0.0.1` and default port is `8787`. Non-localhost hosts are rejected by the CLI entry point. CORS allows only:

- `http://127.0.0.1:5173`
- `http://localhost:5173`

The FastAPI app also validates the HTTP `Host` header. Production hosts are limited to:

- `127.0.0.1`
- `localhost`

Tests may explicitly add `testserver` through the app factory. The app does not use wildcard hosts, wildcard CORS, origin reflection, or CORS as a substitute for Host validation.

Startup prints:

```text
LOCAL SIMULATOR ONLY
REAL HARDWARE DISABLED
```

## Dependency Boundary

FastAPI, Pydantic, and Uvicorn are optional `web` dependencies. Core CLI, simulator tests, and firmware workflows do not import Web modules unless the Web API is explicitly started.

Install for local API development:

```powershell
cd ai-controller
python -m pip install -e '.[web]'
```

Run:

```powershell
powershell -ExecutionPolicy Bypass -File ..\web-console\run-api.ps1
```

or:

```powershell
cd ai-controller
python -m sesame_ai_robot.web
```

## Limits

- Actual received JSON request body maximum: 16 KB. The ASGI body limit counts received `http.request` bytes and does not trust `Content-Length` alone.
- Chat text maximum: 500 characters.
- Confirmation ID maximum: 128 characters.
- Fault name maximum: 80 characters.
- Timeline limit: 1..50.
- Unknown fields are rejected.
- Runtime mode, real-robot enablement, safety severity, ToolCall payloads, and confirmation grants are forbidden request fields.
- POST requests with a body must use `application/json`; `application/json; charset=utf-8` is accepted.
- `POST /api/simulator/reset` and `POST /api/session/reset` accept only an empty JSON object `{}`.

Errors are normalized and do not include traceback, local paths, environment variables, API keys, or Python repr output.

## Provider

The default provider is `mock`. CI must keep `SESAME_AI_PROVIDER=mock` and must not call external AI services.

Developers may explicitly configure the openai-compatible provider through environment variables, but health and error responses must not reveal API keys, credentials, or authorization headers.

`GET /api/health` returns only a safe provider label: `mock`, `openai-compatible`, or `custom`.

## Confirmation Reset Semantics

`POST /api/session/reset` clears conversation state, short-term memory, and Web pending confirmation UI metadata. It does not revoke Runtime confirmation records, and the response includes:

```json
{"runtimeConfirmationsRevoked": false}
```

Any later confirmation submission still goes through `AIInteractionLoop -> ToolExecutor -> RobotRuntime -> ConfirmationStore` and receives the real Runtime result. The Web layer does not fabricate confirmation results.

`POST /api/simulator/reset` fully rebuilds the simulator Runtime graph and ConfirmationStore. Old confirmation IDs become `unknown_id`.

## CI Web Coverage

Core AI tests run before installing the Web optional dependencies to prove the core package does not require FastAPI. CI then installs `.[web]` and runs `ai-controller/run-web-tests.ps1`. That script imports FastAPI, Pydantic, Uvicorn, and `fastapi.testclient`, forces `SESAME_AI_PROVIDER=mock`, runs all `test_web_*.py` tests, prints the total count, and fails if any test is skipped.

## Hardware Status

No ESP32, serial port, camera, microphone, servo, motor, battery, charging dock, firmware upload, or real robot is used by this API.
