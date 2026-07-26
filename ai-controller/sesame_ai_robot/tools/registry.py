from __future__ import annotations

from types import MappingProxyType

from .errors import ToolError, ToolErrorCode
from .models import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._frozen = False

    def register(self, spec: ToolSpec) -> None:
        if self._frozen:
            raise ToolError("tool registry is frozen", ToolErrorCode.FORBIDDEN_TOOL)
        if not isinstance(spec, ToolSpec):
            raise ToolError("tool registry only accepts ToolSpec", ToolErrorCode.FORBIDDEN_TOOL)
        if spec.name in self._tools:
            raise ToolError(f"duplicate tool: {spec.name}", ToolErrorCode.FORBIDDEN_TOOL)
        self._tools[spec.name] = spec

    def freeze(self) -> None:
        self._frozen = True

    @property
    def frozen(self) -> bool:
        return self._frozen

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise ToolError(f"unknown tool: {name}", ToolErrorCode.UNKNOWN_TOOL)
        return self._tools[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def specs(self) -> MappingProxyType:
        return MappingProxyType(dict(self._tools))
