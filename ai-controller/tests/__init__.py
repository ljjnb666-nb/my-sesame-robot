from __future__ import annotations

import sys
from pathlib import Path


AI_CONTROLLER = Path(__file__).resolve().parents[1]
if str(AI_CONTROLLER) not in sys.path:
    sys.path.insert(0, str(AI_CONTROLLER))
