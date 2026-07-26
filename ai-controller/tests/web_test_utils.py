import asyncio
import json
import tempfile
import unittest

from sesame_ai_robot.web.service import RobotSimulatorService


try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


def require_fastapi():
    if TestClient is None:
        raise unittest.SkipTest("FastAPI optional web dependency is not installed")


def make_service(testcase: unittest.TestCase, **kwargs):
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    service = RobotSimulatorService(memory_storage_path=f"{tmp.name}/memory.json", **kwargs)
    return service, tmp


def make_client(testcase: unittest.TestCase, service=None, **kwargs):
    require_fastapi()
    from sesame_ai_robot.web.app import create_app
    from sesame_ai_robot.web.security import TEST_ALLOWED_HOSTS

    if service is None:
        service, _tmp = make_service(testcase)
    app = create_app(service=service, allowed_hosts=TEST_ALLOWED_HOSTS, **kwargs)
    return TestClient(app, raise_server_exceptions=False), service


def post_json(client, path, payload):
    return client.post(path, json=payload, headers={"host": "testserver"})


def get(client, path, **headers):
    merged = {"host": "testserver", **headers}
    return client.get(path, headers=merged)


def run_asgi_request(app, *, method="POST", path="/api/chat", headers=None, chunks=()):
    async def _run():
        sent = []
        events = []
        chunk_list = list(chunks)
        for index, chunk in enumerate(chunk_list):
            events.append({
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(chunk_list) - 1,
            })
        if not events:
            events.append({"type": "http.request", "body": b"", "more_body": False})

        async def receive():
            if events:
                return events.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        raw_headers = [(b"host", b"testserver")]
        for key, value in (headers or {}).items():
            raw_headers.append((key.lower().encode("latin1"), value.encode("latin1")))
        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode("ascii"),
                "query_string": b"",
                "headers": raw_headers,
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        status = next(item["status"] for item in sent if item["type"] == "http.response.start")
        body = b"".join(item.get("body", b"") for item in sent if item["type"] == "http.response.body")
        return status, body, sent

    return asyncio.run(_run())


def json_body(body: bytes):
    return json.loads(body.decode("utf-8"))
