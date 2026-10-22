import json
from pathlib import Path

from brawrec.bmff.boxes import p32
from brawrec.cli import main
from tests.fixtures import box
from tests.fixtures import synthetic_braw


def test_analyze_command_writes_reports(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    out = tmp_path / "reports"

    rc = main(["analyze", str(source), "--out", str(out)])

    assert rc == 0
    assert (out / "analysis.json").exists()
    assert (out / "analysis.md").exists()


def test_repair_refusal_writes_report_without_candidate(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    output = tmp_path / "candidate.braw"
    report_dir = tmp_path / "reports"

    rc = main(["repair", str(source), "--out", str(output), "--report", str(report_dir)])

    assert rc == 1
    assert not output.exists()
    payload = json.loads((report_dir / "repair.json").read_text(encoding="utf-8"))
    assert payload == {
        "confidence": "not_assessed",
        "hidden_frame_count": 0,
        "output": str(output.resolve()),
        "refusal_reason": "no hidden frames to repair",
        "source": str(source.resolve()),
        "status": "refused",
    }
    assert "no hidden frames to repair" in (report_dir / "repair.md").read_text(encoding="utf-8")


def test_repair_same_source_refusal_writes_report_without_candidate(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    original = source.read_bytes()
    report_dir = tmp_path / "reports"

    rc = main(["repair", str(source), "--out", str(source), "--report", str(report_dir)])

    assert rc == 1
    payload = json.loads((report_dir / "repair.json").read_text(encoding="utf-8"))
    assert payload["status"] == "refused"
    assert payload["refusal_reason"] == "output path is the same as source"
    assert payload["source"] == str(source.resolve())
    assert payload["output"] == str(source.resolve())
    assert payload["hidden_frame_count"] == 0
    assert payload["confidence"] == "not_assessed"
    assert source.read_bytes() == original


def test_repair_malformed_source_writes_refusal_reports(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(b"not a braw file")
    output = tmp_path / "candidate.braw"
    report_dir = tmp_path / "reports"

    rc = main(["repair", str(source), "--out", str(output), "--report", str(report_dir)])

    assert rc == 1
    payload = json.loads((report_dir / "repair.json").read_text(encoding="utf-8"))
    assert payload["status"] == "refused"
    assert payload["refusal_reason"]
    assert payload["source"] == str(source.resolve())
    assert payload["output"] == str(output.resolve())
    assert payload["hidden_frame_count"] is None
    assert payload["confidence"] == "not_assessed"
    assert "Repair" in (report_dir / "repair.md").read_text(encoding="utf-8")


def test_repair_truncated_tkhd_writes_refusal_reports(tmp_path: Path):
    source = tmp_path / "truncated-tkhd.braw"
    mdat_size = 2048
    moov = box(b"moov", box(b"trak", box(b"tkhd", b"\0\0\0\0")))
    source.write_bytes(
        p32(1) + b"mdat" + mdat_size.to_bytes(8, "big")
        + b"\0" * (mdat_size - 16) + moov + b"tail"
    )
    output = tmp_path / "candidate.braw"
    report_dir = tmp_path / "reports"

    rc = main(["repair", str(source), "--out", str(output), "--report", str(report_dir)])

    assert rc == 1
    assert not output.exists()
    payload = json.loads((report_dir / "repair.json").read_text(encoding="utf-8"))
    assert payload["status"] == "refused"
    assert payload["hidden_frame_count"] is None
    assert "tuple index out of range" not in payload["refusal_reason"]
    assert (report_dir / "repair.md").exists()


def test_verify_command_writes_reports(tmp_path: Path):
    candidate = tmp_path / "candidate.braw"
    candidate.write_bytes(synthetic_braw([100], [256], 2048))
    out = tmp_path / "reports"

    rc = main(["verify", str(candidate), "--out", str(out)])

    assert rc == 0
    payload = json.loads((out / "verify.json").read_text(encoding="utf-8"))
    assert payload["candidate"] == str(candidate.resolve())
    assert payload["track_count"] == 1
    assert (out / "verify.md").exists()
