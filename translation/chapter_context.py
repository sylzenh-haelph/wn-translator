from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextState:
    scene: str = ""
    active_characters: list[str] = field(default_factory=list)
    current_situation: str = ""
    references: list[str] = field(default_factory=list)
    style_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "scene": self.scene,
            "active_characters": self.active_characters,
            "current_situation": self.current_situation,
            "references": self.references,
            "style_state": self.style_state,
        }
