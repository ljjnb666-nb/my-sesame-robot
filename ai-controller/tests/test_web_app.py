import importlib
import importlib.util
import tempfile
import unittest

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI optional web dependency is not installed")

from fastapi.testclient import TestClient

from sesame_ai_robot.web.app import create_app
from sesame_ai_robot.web.security import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKERS
from sesame_ai_robot.web.service import RobotSimulatorService


class WebAppTest(unittest.TestCase):
    def make_client(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        service = RobotSimulatorService(memory_storage_path=f"{self.tmp.name}/memory.json")
        return TestClient(create_app(service=service), raise_server_exceptions=False)

    def test_create_app_does_not_create_service_until_needed(self):
        app = create_app()
        self.assertIsNone(app.state.service)

    def test_health_route(self):
        client = self.make_client()
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_state_route(self):
        client = self.make_client()
        response = client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["runtimeMode"], "simulator")

    def test_chat_route(self):
        client = self.make_client()
        response = client.post("/api/chat", json={"text": "battery", "confirmationId": None})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_timeline_route(self):
        client = self.make_client()
        response = client.get("/api/timeline?limit=20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["limit"], 20)

    def test_fault_routes(self):
        client = self.make_client()
        injected = client.post("/api/simulator/faults", json={"fault": "servo_stuck"})
        self.assertEqual(injected.status_code, 200)
        self.assertIn("servo_stuck", injected.json()["state"]["faults"])
        cleared = client.delete("/api/simulator/faults/servo_stuck")
        self.assertEqual(cleared.status_code, 200)
        self.assertNotIn("servo_stuck", cleared.json()["state"]["faults"])

    def test_reset_routes(self):
        client = self.make_client()
        self.assertEqual(client.post("/api/simulator/reset").status_code, 200)
        self.assertEqual(client.post("/api/session/reset").status_code, 200)

    def test_default_bind_and_worker_constants(self):
        self.assertEqual(DEFAULT_HOST, "127.0.0.1")
        self.assertEqual(DEFAULT_PORT, 8787)
        self.assertEqual(DEFAULT_WORKERS, 1)

    def test_core_package_import_does_not_import_fastapi_web_app(self):
        package = importlib.import_module("sesame_ai_robot")
        self.assertFalse(hasattr(package, "app"))


if __name__ == "__main__":
    unittest.main()
