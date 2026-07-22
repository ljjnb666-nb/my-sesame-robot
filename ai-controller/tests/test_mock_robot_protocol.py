import json
import unittest
from urllib import error, request

from sesame_ai_robot.mock_robot import MockRobotServer


class MockRobotProtocolTest(unittest.TestCase):
    def setUp(self):
        self.server = MockRobotServer(port=0)
        self.server.start()

    def tearDown(self):
        self.server.stop()

    def post_json(self, payload):
        return self.post_raw(json.dumps(payload))

    def post_raw(self, body: str):
        http_request = request.Request(
            f"{self.server.url}/api/command",
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        opener = request.build_opener(request.ProxyHandler({}))
        try:
            with opener.open(http_request, timeout=1.0) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def post_bytes(self, body: bytes):
        http_request = request.Request(
            f"{self.server.url}/api/command",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        opener = request.build_opener(request.ProxyHandler({}))
        try:
            with opener.open(http_request, timeout=1.0) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def status(self):
        with request.build_opener(request.ProxyHandler({})).open(f"{self.server.url}/api/status", timeout=1.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_unknown_command_returns_400_and_does_not_pollute_state(self):
        status_code, payload = self.post_raw('{"command":"fly"}')

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "unknown_command")
        status = self.status()
        self.assertEqual(status["currentCommand"], "")
        self.assertEqual(status["motionState"], "idle")

    def test_empty_command_returns_400(self):
        status_code, payload = self.post_json({"command": ""})

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "empty_command")

    def test_missing_command_and_face_returns_400(self):
        status_code, payload = self.post_json({})

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "missing_command")

    def test_invalid_json_returns_400(self):
        status_code, payload = self.post_raw("{not-json")

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def test_face_only_request_still_succeeds(self):
        status_code, payload = self.post_json({"face": "happy"})

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["face"], "happy")
        self.assertEqual(self.status()["currentFace"], "happy")

    def test_rejects_non_string_command(self):
        for value in (123, ["forward"], True):
            status_code, payload = self.post_json({"command": value})
            self.assertEqual(status_code, 400)
            self.assertEqual(payload["error"], "invalid_command_type")

    def test_rejects_non_object_json(self):
        for raw in ('["forward"]', '"forward"'):
            status_code, payload = self.post_raw(raw)
            self.assertEqual(status_code, 400)
            self.assertEqual(payload["error"], "invalid_payload")

    def test_rejects_invalid_face_values(self):
        status_code, payload = self.post_json({"face": 7})
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "invalid_face_type")

        status_code, payload = self.post_json({"face": ""})
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "empty_face")

        status_code, payload = self.post_json({"face": "not_a_face"})
        self.assertEqual(status_code, 400)
        self.assertEqual(payload["error"], "unknown_face")

    def test_oversized_payload_returns_413(self):
        status_code, payload = self.post_bytes(b'{"command":"forward","padding":"' + (b"x" * 600) + b'"}')

        self.assertEqual(status_code, 413)
        self.assertEqual(payload["error"], "payload_too_large")

    def test_emergency_stop_rejects_normal_motion(self):
        self.post_json({"command": "emergency_stop"})

        status_code, payload = self.post_json({"command": "forward"})

        self.assertEqual(status_code, 409)
        self.assertEqual(payload["error"], "emergency_stop_active")
        status = self.status()
        self.assertTrue(status["emergencyStopActive"])
        self.assertEqual(status["currentCommand"], "")

    def test_heartbeat_does_not_restore_motion_during_emergency_stop(self):
        self.post_json({"command": "forward"})
        self.post_json({"command": "emergency_stop"})

        status_code, payload = self.post_json({"command": "heartbeat"})

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["command"], "heartbeat")
        status = self.status()
        self.assertTrue(status["emergencyStopActive"])
        self.assertEqual(status["currentCommand"], "")


if __name__ == "__main__":
    unittest.main()
