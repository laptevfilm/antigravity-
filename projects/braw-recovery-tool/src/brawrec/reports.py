from __future__ import annotations

import json
from pathlib import Path


def write_json_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_markdown_report(path: Path, title: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = [f"# {title}"]
    for key, value in payload.items():
        sections.extend((f"## {key}", json.dumps(value, ensure_ascii=False, indent=2)))
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
