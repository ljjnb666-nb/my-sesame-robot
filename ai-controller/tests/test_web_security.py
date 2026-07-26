import os
import unittest

from sesame_ai_robot.web.app import create_app
from sesame_ai_robot.web.security import DEFAULT_ALLOWED_ORIGINS, MAX_BODY_BYTES, TEST_ALLOWED_HOSTS, assert_local_host, sanitize_text

from web_test_utils import get, json_body, make_client, make_service, post_json, require_fastapi, run_asgi_request


class WebSecurityTest(unittest.TestCase):
    def setUp(self):
        require_fastapi()
        self.client, self.service = make_client(self)

    def test_localhost_host_policy(self):
        self.assertEqual(assert_local_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(assert_local_host("localhost"), "127.0.0.1")
        with self.assertRaises(ValueError):
            assert_local_host("0.0.0.0")

    def test_trusted_host_policy(self):
        service, _tmp = make_service(self)
        from fastapi.testclient import TestClient

        client = TestClient(create_app(service=service, allowed_hosts=TEST_ALLOWED_HOSTS), raise_server_exceptions=False)
        self.assertEqual(client.get("/api/health", headers={"host": "127.0.0.1"}).status_code, 200)
        self.assertEqual(client.get("/api/health", headers={"host": "localhost"}).status_code, 200)
        self.assertEqual(client.get("/api/health", headers={"host": "testserver"}).status_code, 200)
        self.assertEqual(client.get("/api/health", headers={"host": "example.com"}).status_code, 400)
        self.assertEqual(client.get("/api/health", headers={"host": "evil.localhost.example.com"}).status_code, 400)

    def test_cors_allows_only_local_frontend(self):
        response = self.client.options(
            "/api/health",
            headers={
                "host": "testserver",
                "Origin": DEFAULT_ALLOWED_ORIGINS[0],
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.headers.get("access-control-allow-origin"), DEFAULT_ALLOWED_ORIGINS[0])
        denied = self.client.options(
            "/api/health",
            headers={
                "host": "testserver",
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(denied.headers.get("access-control-allow-origin"), "https://example.com")

    def test_origin_does_not_bypass_host_limit(self):
        response = self.client.get(
            "/api/health",
            headers={"host": "example.com", "origin": DEFAULT_ALLOWED_ORIGINS[0]},
        )
        self.assertEqual(response.status_code, 400)

    def test_health_uses_safe_provider_label(self):
        class EvilProvider:
            name = "openai-compatible sk-secret C:\\Users\\secret"

            def generate_intent(self, request):
                raise AssertionError("not used")

        service, _tmp = make_service(self, provider=EvilProvider())
        self.assertEqual(service.health()["provider"], "custom")
        self.assertNotIn("sk-secret", str(service.health()))

    def test_health_does_not_leak_provider_environment(self):
        os.environ["SESAME_AI_API_KEY"] = "sk-secret-value"
        os.environ["SESAME_AI_BASE_URL"] = "https://user:pass@example.test"
        try:
            payload = get(self.client, "/api/health").json()
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
                response = post_json(self.client, "/api/chat", payload)
                self.assertGreaterEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_content_type_boundaries(self):
        self.assertEqual(self.client.post("/api/chat", data="{}", headers={"host": "testserver", "content-type": "text/plain"}).status_code, 415)
        self.assertEqual(self.client.post("/api/chat", data="text=battery", headers={"host": "testserver", "content-type": "application/x-www-form-urlencoded"}).status_code, 415)
        self.assertEqual(self.client.post("/api/chat", files={"file": ("x.txt", b"x")}, headers={"host": "testserver"}).status_code, 415)
        accepted = self.client.post(
            "/api/chat",
            data='{"text":"battery"}',
            headers={"host": "testserver", "content-type": "application/json; charset=utf-8"},
        )
        self.assertEqual(accepted.status_code, 200)

    def test_missing_content_type_with_body_is_rejected_without_content_length(self):
        app = create_app(service=self.service, allowed_hosts=TEST_ALLOWED_HOSTS)
        status, body, _sent = run_asgi_request(app, headers={}, chunks=(b'{"text":"battery"}',))
        self.assertEqual(status, 415)
        self.assertEqual(json_body(body)["error"]["code"], "invalid_request")

    def test_actual_body_limit_does_not_depend_on_content_length(self):
        app = create_app(service=self.service, allowed_hosts=TEST_ALLOWED_HOSTS)
        oversized = b'{"text":"' + (b"x" * (MAX_BODY_BYTES + 1)) + b'"}'
        for headers in (
            {"content-type": "application/json"},
            {"content-type": "application/json", "content-length": "10"},
        ):
            with self.subTest(headers=headers):
                status, body, _sent = run_asgi_request(app, headers=headers, chunks=(oversized,))
                self.assertEqual(status, 413)
                payload = json_body(body)
                self.assertEqual(payload["error"]["code"], "request_too_large")
                self.assertNotIn("x" * 100, str(payload))

    def test_chunked_oversized_body_is_rejected(self):
        app = create_app(service=self.service, allowed_hosts=TEST_ALLOWED_HOSTS)
        status, body, _sent = run_asgi_request(
            app,
            headers={"content-type": "application/json"},
            chunks=(b'{"text":"', b"x" * MAX_BODY_BYTES, b'"}'),
        )
        self.assertEqual(status, 413)
        self.assertEqual(json_body(body)["error"]["code"], "request_too_large")

    def test_content_length_oversized_rejected_before_handler(self):
        class SpyService:
            chat_calls = 0

            def chat(self, text, confirmation_id=None):
                self.chat_calls += 1
                return {"status": "ok"}

        spy = SpyService()
        app = create_app(service=spy, allowed_hosts=TEST_ALLOWED_HOSTS)
        status, _body, _sent = run_asgi_request(
            app,
            headers={"content-type": "application/json", "content-length": str(MAX_BODY_BYTES + 1)},
            chunks=(b'{"text":"battery"}',),
        )
        self.assertEqual(status, 413)
        self.assertEqual(spy.chat_calls, 0)

    def test_exact_body_limit_is_not_request_too_large(self):
        app = create_app(service=self.service, allowed_hosts=TEST_ALLOWED_HOSTS)
        status, _body, _sent = run_asgi_request(
            app,
            path="/api/session/reset",
            headers={"content-type": "application/json"},
            chunks=(b" " * MAX_BODY_BYTES,),
        )
        self.assertNotEqual(status, 413)

    def test_invalid_json_has_safe_error(self):
        response = self.client.post("/api/chat", data="{bad", headers={"host": "testserver", "content-type": "application/json"})
        self.assertGreaterEqual(response.status_code, 400)
        encoded = str(response.json())
        self.assertNotIn("Traceback", encoded)
        self.assertNotIn("C:\\Users", encoded)
        self.assertNotIn("sk-", encoded)

    def test_404_has_safe_error(self):
        response = get(self.client, "/api/missing")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_route_exception_is_sanitized(self):
        class BrokenService:
            def health(self):
                raise RuntimeError("boom C:\\Users\\secret\\file.py sk-secret\nBearer token")

        from fastapi.testclient import TestClient

        client = TestClient(create_app(service=BrokenService(), allowed_hosts=TEST_ALLOWED_HOSTS), raise_server_exceptions=False)
        response = client.get("/api/health", headers={"host": "testserver"})
        self.assertEqual(response.status_code, 500)
        encoded = str(response.json())
        self.assertNotIn("Traceback", encoded)
        self.assertNotIn("C:\\Users", encoded)
        self.assertNotIn("sk-secret", encoded)
        self.assertNotIn("\n", encoded)
        self.assertNotIn("Bearer token", encoded)

    def test_rejects_file_shell_and_proxy_fields(self):
        for payload in (
            {"text": "battery", "filePath": "C:\\Users\\x"},
            {"text": "battery", "shell": "dir"},
            {"text": "battery", "proxyUrl": "http://example.com"},
        ):
            response = post_json(self.client, "/api/chat", payload)
            self.assertGreaterEqual(response.status_code, 400)

    def test_sanitize_text_filters_multiline_secrets(self):
        text = sanitize_text("line1\nline2\rsk-secret Bearer token C:\\Users\\secret\\file.py api_key=hidden")
        self.assertNotIn("\n", text)
        self.assertNotIn("\r", text)
        self.assertNotIn("sk-secret", text)
        self.assertNotIn("Bearer token", text)
        self.assertNotIn("C:\\Users", text)
        self.assertNotIn("hidden", text)


if __name__ == "__main__":
    unittest.main()
