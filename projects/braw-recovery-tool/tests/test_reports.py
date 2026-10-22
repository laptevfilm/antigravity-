import json
from pathlib import Path

from brawrec.reports import write_json_report, write_markdown_report


def test_write_json_report_creates_parent_and_pretty_json(tmp_path: Path):
    out = tmp_path / "reports" / "analysis.json"
    write_json_report(out, {"hidden_frames": 24})
    assert json.loads(out.read_text(encoding="utf-8")) == {"hidden_frames": 24}
    assert "\n  " in out.read_text(encoding="utf-8")


def test_write_markdown_report_contains_title_and_values(tmp_path: Path):
    out = tmp_path / "analysis.md"
    write_markdown_report(out, "Analysis", {"hidden_frames": 24})
    text = out.read_text(encoding="utf-8")
    assert "# Analysis" in text
    assert "hidden_frames" in text
    assert "24" in text
