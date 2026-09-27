from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextRun:
    text: str
    formatting: dict[str, Any] = field(default_factory=dict)


@dataclass
class Paragraph:
    id: str
    runs: list[TextRun] = field(default_factory=list)
    style: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass
class Document:
    title: str = ""
    author: str = ""
    paragraphs: list[Paragraph] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
