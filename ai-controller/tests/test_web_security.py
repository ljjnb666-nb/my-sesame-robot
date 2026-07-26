import os
import importlib.util
import tempfile
import unittest

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI optional web dependency is not installed")

from fastapi.testclient import TestClient

from sesame_ai_robot.web.app import create_app
from sesame_ai_robot.web.security import DEFAULT_ALLOWED_ORIGINS, assert_local_host
from sesame_ai_robot.web.service import RobotSimulatorService


class WebSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        service = RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")
        self.client = TestClient(create_app(service=service), raise_server_exceptions=False)

    def test_localhost_host_policy(self):
        self.assertEqual(assert_local_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(assert_local_host("localhost"), "127.0.0.1")
        with self.assertRaises(ValueError):
            assert_local_host("0.0.0.0")

    def test_cors_allows_only_local_frontend(self):
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": DEFAULT_ALLOWED_ORIGINS[0],
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), DEFAULT_ALLOWED_ORIGINS[0])
        denied = self.client.options(
            "/api/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(denied.headers.get("access-control-allow-origin"), "https://example.com")

    def test_health_does_not_leak_provider_secrets(self):
        os.environ["SESAME_AI_API_KEY"] = "sk-secret-value"
        os.environ["SESAME_AI_BASE_URL"] = "https://user:pass@example.test"
        try:
            payload = self.client.get("/api/health").json()
        finally:
            os.environ.pop("SESAME_AI_API_KEY", None)
            os.environ.pop("SESAME_AI_BASE_URL", None)
        encoded = str(payload)
        self.assertNotIn("sk-secret-value", encoded)
        self.assertNotIn("user:pass", encoded)

    def test_chat_rejects_invalid_requests(self):
        cases = [
            {},
            {"text": ""},
            {"text": "   "},
            {"text": 123},
            {"text": "x", "extra": True},
            {"text": "x", "runtimeMode": "real_robot"},
            {"text": "x", "allowRealRobot": True},
            {"text": "x", "confirmationGrant": "grant"},
            {"text": "x", "confirmationId": "x" * 129},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/api/chat", json=payload)
                self.assertGreaterEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_rejects_non_json_and_oversized_body(self):
        non_json = self.client.post("/api/chat", data="text=battery", headers={"content-type": "text/plain"})
        self.assertEqual(non_json.status_code, 415)
        oversized = self.client.post(
            "/api/chat",
            data='{"text":"' + ("x" * 17000) + '"}',
            headers={"content-type": "application/json"},
        )
        self.assertEqual(oversized.status_code, 413)

    def test_invalid_json_has_safe_error(self):
        response = self.client.post("/api/chat", data="{bad", headers={"content-type": "application/json"})
        self.assertGreaterEqual(response.status_code, 400)
        encoded = str(response.json())
        self.assertNotIn("Traceback", encoded)
        self.assertNotIn("C:\\Users", encoded)

    def test_404_has_safe_error(self):
        response = self.client.get("/api/missing")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_route_exception_is_sanitized(self):
        class BrokenService(RobotSimulatorService):
            def health(self):
                raise RuntimeError("boom C:\\Users\\secret\\file.py sk-secret")

        with tempfile.TemporaryDirectory() as tmp:
            client = TestClient(
                create_app(service=BrokenService(memory_storage_path=f"{tmp}/memory.json")),
                raise_server_exceptions=False,
            )
            response = client.get("/api/health")
            self.assertEqual(response.status_code, 500)
            encoded = str(response.json())
            self.assertNotIn("Traceback", encoded)
            self.assertNotIn("C:\\Users", encoded)
            self.assertNotIn("sk-secret", encoded)

    def test_rejects_file_shell_and_proxy_fields(self):
        for payload in (
            {"text": "battery", "filePath": "C:\\Users\\x"},
            {"text": "battery", "shell": "dir"},
            {"text": "battery", "proxyUrl": "http://example.com"},
        ):
            response = self.client.post("/api/chat", json=payload)
            self.assertGreaterEqual(response.status_code, 400)

    def test_openapi_schema_generates(self):
        schema = self.client.app.openapi()
        self.assertIn("/api/chat", schema["paths"])


if __name__ == "__main__":
    unittest.main()
