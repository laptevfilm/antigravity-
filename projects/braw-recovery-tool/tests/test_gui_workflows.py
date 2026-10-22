from pathlib import Path

import pytest

from brawrec.gui_workflows import (
    default_candidate_path,
    default_output_dir,
    recover_source,
    validate_candidate_path,
    verify_candidate,
)


def test_default_output_dir_uses_runs_and_source_stem(tmp_path: Path):
    source = tmp_path / "Clip Name.braw"
    root = tmp_path / "project"

    assert default_output_dir(source, root) == root / "runs" / "Clip Name"


def test_default_candidate_path_uses_source_stem(tmp_path: Path):
    source = tmp_path / "A001_010101.braw"
    output_dir = tmp_path / "runs" / "A001_010101"

    assert default_candidate_path(source, output_dir) == output_dir / "A001_010101_candidate.braw"


def test_validate_candidate_path_rejects_source_path(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(b"sample")

    with pytest.raises(ValueError, match="same as the source"):
        validate_candidate_path(source, source)


def test_recover_source_rejects_report_dir_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "clip.braw"
    candidate = tmp_path / "selected" / "clip_candidate.braw"
    report_dir = tmp_path / "reports"

    def fail_repair(*args: object) -> None:
        raise AssertionError("_repair must not run for a report directory mismatch")

    monkeypatch.setattr("brawrec.gui_workflows._repair", fail_repair)

    with pytest.raises(ValueError, match="report directory"):
        recover_source(source, candidate, report_dir)


def test_recover_source_accepts_matching_report_dir_through_to_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "clip.braw"
    candidate = tmp_path / "selected" / "clip_candidate.braw"
    report_dir = candidate.parent
    calls = []

    def fake_repair(repair_source: Path, output: Path, repair_report_dir: Path) -> None:
        calls.append((repair_source, output, repair_report_dir))

    monkeypatch.setattr("brawrec.gui_workflows._repair", fake_repair)

    result = recover_source(source, candidate, report_dir)

    assert calls == [(source, candidate, report_dir)]
    assert result == {
        "candidate": str(candidate.resolve()),
        "report_dir": str(report_dir.resolve()),
    }


def test_verify_candidate_rejects_report_dir_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    candidate = tmp_path / "selected" / "clip_candidate.braw"
    report_dir = tmp_path / "reports"

    def fail_verify(*args: object) -> None:
        raise AssertionError("_verify must not run for a report directory mismatch")

    monkeypatch.setattr("brawrec.gui_workflows._verify", fail_verify)

    with pytest.raises(ValueError, match="report directory"):
        verify_candidate(candidate, report_dir)


def test_gui_success_message_formats_result_for_users():
    from brawrec.gui import format_success_message

    message = format_success_message(
        "Verification complete.",
        {"candidate": "C:/runs/clip_candidate.braw", "report_dir": "C:/runs"},
    )

    assert message == (
        "Verification complete.\n"
        "Candidate: C:/runs/clip_candidate.braw\n"
        "Reports: C:/runs"
    )
    assert "{" not in message


def test_gui_module_imports_without_opening_window():
    from brawrec import gui

    assert gui.BrawRecoveryApp is not None
    assert callable(gui.main)
