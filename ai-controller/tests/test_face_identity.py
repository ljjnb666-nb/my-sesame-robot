import tempfile
import unittest
from pathlib import Path

from sesame_ai_robot.camera import MockCameraSource
from sesame_ai_robot.face_identity import (
    FaceIdentity,
    LocalFaceStore,
    MockFaceRecognizer,
    recognition_to_jsonable,
)


class FaceIdentityTest(unittest.TestCase):
    def test_local_face_store_registers_lists_and_deletes_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFaceStore(Path(temp_dir))

            identity = store.register_identity("owner", "Owner")
            self.assertEqual(identity.identity_id, "owner")
            self.assertEqual(store.list_identities()[0].display_name, "Owner")
            self.assertTrue(store.delete_identity("owner"))
            self.assertEqual(store.list_identities(), ())

    def test_mock_recognizer_requires_threshold(self):
        identity = FaceIdentity("owner", "Owner", 0.0)
        frame = MockCameraSource().read()

        low = MockFaceRecognizer(identity, confidence=0.7, threshold=0.75).identify(frame)
        high = MockFaceRecognizer(identity, confidence=0.8, threshold=0.75).identify(frame)
        missing = MockFaceRecognizer(None, confidence=0.99, threshold=0.75).identify(frame)

        self.assertFalse(low.confirmed)
        self.assertTrue(high.confirmed)
        self.assertFalse(missing.confirmed)

    def test_recognition_to_jsonable_does_not_invent_owner(self):
        result = MockFaceRecognizer(None, confidence=0.99, threshold=0.75).identify(MockCameraSource().read())

        payload = recognition_to_jsonable(result)
        self.assertFalse(payload["confirmed"])
        self.assertIsNone(payload["identity"])


if __name__ == "__main__":
    unittest.main()
