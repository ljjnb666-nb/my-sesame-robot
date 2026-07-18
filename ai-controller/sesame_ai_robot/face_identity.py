from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Protocol

from .camera import CameraFrame


@dataclass(frozen=True)
class FaceIdentity:
    identity_id: str
    display_name: str
    created_at: float


@dataclass(frozen=True)
class FaceRecognitionResult:
    identity: FaceIdentity | None
    confidence: float
    threshold: float

    @property
    def confirmed(self) -> bool:
        return self.identity is not None and self.confidence >= self.threshold


class FaceRecognizer(Protocol):
    def identify(self, frame: CameraFrame) -> FaceRecognitionResult:
        ...


class LocalFaceStore:
    def __init__(self, root: Path):
        self.root = root
        self.identities_dir = root / "identities"

    def ensure_layout(self) -> None:
        self.identities_dir.mkdir(parents=True, exist_ok=True)

    def register_identity(self, identity_id: str, display_name: str) -> FaceIdentity:
        if not identity_id.strip():
            raise ValueError("identity_id is required")
        if not display_name.strip():
            raise ValueError("display_name is required")

        self.ensure_layout()
        identity = FaceIdentity(identity_id=identity_id, display_name=display_name, created_at=time.time())
        path = self._identity_path(identity_id)
        path.write_text(json.dumps(identity.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        return identity

    def delete_identity(self, identity_id: str) -> bool:
        path = self._identity_path(identity_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_identities(self) -> tuple[FaceIdentity, ...]:
        self.ensure_layout()
        identities: list[FaceIdentity] = []
        for path in sorted(self.identities_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            identities.append(FaceIdentity(**payload))
        return tuple(identities)

    def _identity_path(self, identity_id: str) -> Path:
        safe_id = identity_id.replace("/", "_").replace("\\", "_")
        return self.identities_dir / f"{safe_id}.json"


class MockFaceRecognizer:
    def __init__(self, identity: FaceIdentity | None = None, confidence: float = 0.0, threshold: float = 0.75):
        self.identity = identity
        self.confidence = confidence
        self.threshold = threshold

    def identify(self, frame: CameraFrame) -> FaceRecognitionResult:
        return FaceRecognitionResult(identity=self.identity, confidence=self.confidence, threshold=self.threshold)


def recognition_to_jsonable(result: FaceRecognitionResult) -> dict[str, object]:
    return {
        "confirmed": result.confirmed,
        "confidence": result.confidence,
        "threshold": result.threshold,
        "identity": None if result.identity is None else {
            "identityId": result.identity.identity_id,
            "displayName": result.identity.display_name,
            "createdAt": result.identity.created_at,
        },
    }
