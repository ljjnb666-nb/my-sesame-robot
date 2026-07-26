import importlib
import unittest

from sesame_ai_robot.web.app import create_app
from sesame_ai_robot.web.security import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKERS, TEST_ALLOWED_HOSTS

from web_test_utils import get, make_client, post_json, require_fastapi


class WebAppTest(unittest.TestCase):
    def setUp(self):
        require_fastapi()

    def test_create_app_does_not_create_service_until_needed(self):
        app = create_app(allowed_hosts=TEST_ALLOWED_HOSTS)
        self.assertIsNone(app.state.service)

    def test_health_route(self):
        client, _service = make_client(self)
        response = get(client, "/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_state_route(self):
        client, _service = make_client(self)
        response = get(client, "/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["runtimeMode"], "simulator")

    def test_chat_route(self):
        client, _service = make_client(self)
        response = post_json(client, "/api/chat", {"text": "battery", "confirmationId": None})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_timeline_route(self):
        client, _service = make_client(self)
        response = get(client, "/api/timeline?limit=20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["limit"], 20)

    def test_fault_routes(self):
        client, _service = make_client(self)
        injected = post_json(client, "/api/simulator/faults", {"fault": "servo_stuck"})
        self.assertEqual(injected.status_code, 200)
        self.assertIn("servo_stuck", injected.json()["state"]["faults"])
        cleared = client.delete("/api/simulator/faults/servo_stuck", headers={"host": "testserver"})
        self.assertEqual(cleared.status_code, 200)
        self.assertNotIn("servo_stuck", cleared.json()["state"]["faults"])

    def test_reset_routes_require_empty_json_object(self):
        client, _service = make_client(self)
        self.assertEqual(post_json(client, "/api/simulator/reset", {}).status_code, 200)
        self.assertEqual(post_json(client, "/api/session/reset", {}).status_code, 200)
        self.assertGreaterEqual(post_json(client, "/api/simulator/reset", {"runtimeMode": "simulator"}).status_code, 400)
        self.assertGreaterEqual(client.post("/api/session/reset", json=[], headers={"host": "testserver"}).status_code, 400)
        self.assertGreaterEqual(client.post("/api/session/reset", data='"x"', headers={"host": "testserver", "content-type": "application/json"}).status_code, 400)

    def test_default_bind_and_worker_constants(self):
        self.assertEqual(DEFAULT_HOST, "127.0.0.1")
        self.assertEqual(DEFAULT_PORT, 8787)
        self.assertEqual(DEFAULT_WORKERS, 1)

    def test_core_package_import_does_not_import_fastapi_web_app(self):
        package = importlib.import_module("sesame_ai_robot")
        self.assertFalse(hasattr(package, "app"))

    def test_openapi_schema_generates(self):
        client, _service = make_client(self)
        schema = client.app.openapi()
        self.assertIn("/api/chat", schema["paths"])

    def test_chat_route_only_calls_service_chat(self):
        class SpyService:
            def __init__(self):
                self.chat_calls = []

            def chat(self, text, confirmation_id=None):
                self.chat_calls.append((text, confirmation_id))
                return {"status": "ok", "message": "done"}

        from fastapi.testclient import TestClient

        service = SpyService()
        client = TestClient(create_app(service=service, allowed_hosts=TEST_ALLOWED_HOSTS), raise_server_exceptions=False)
        response = client.post("/api/chat", json={"text": "battery", "confirmationId": "abc"}, headers={"host": "testserver"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.chat_calls, [("battery", "abc")])
        self.assertFalse(hasattr(service, "runtime"))
        self.assertFalse(hasattr(service, "hardware"))
        self.assertFalse(hasattr(service, "confirmation_store"))

    def test_fault_route_only_calls_service_fault_method(self):
        class SpyService:
            def __init__(self):
                self.fault_calls = []

            def inject_fault(self, fault):
                self.fault_calls.append(fault)
                return {"status": "ok", "fault": fault}

        from fastapi.testclient import TestClient

        service = SpyService()
        client = TestClient(create_app(service=service, allowed_hosts=TEST_ALLOWED_HOSTS), raise_server_exceptions=False)
        response = client.post("/api/simulator/faults", json={"fault": "servo_stuck"}, headers={"host": "testserver"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.fault_calls, ["servo_stuck"])
        self.assertFalse(hasattr(service, "tool_executor"))
        self.assertFalse(hasattr(service, "runtime"))


if __name__ == "__main__":
    unittest.main()
