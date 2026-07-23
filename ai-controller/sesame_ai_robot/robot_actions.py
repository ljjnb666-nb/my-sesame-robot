from __future__ import annotations


SUPPORTED_ROBOT_ACTIONS = frozenset({
    "stop",
    "emergency_stop",
    "wave",
    "walk_forward",
    "walk_backward",
    "turn_left",
    "turn_right",
    "stand",
    "rest",
})
