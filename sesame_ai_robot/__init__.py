from __future__ import annotations

import sys
from pathlib import Path


REAL_PACKAGE = Path(__file__).resolve().parents[1] / "ai-controller" / "sesame_ai_robot"
AI_CONTROLLER = REAL_PACKAGE.parent
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))
if REAL_PACKAGE.exists() and str(REAL_PACKAGE) not in __path__:
    __path__.append(str(REAL_PACKAGE))
