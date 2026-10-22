from __future__ import annotations

from pathlib import Path

from brawrec.cli import _repair, _verify, _write_analysis_reports


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_output_dir(source: Path, root: Path | None = None) -> Path:
    base = project_root() if root is None else root
    return base / "runs" / source.stem


def default_candidate_path(source: Path, output_dir: Path) -> Path:
    return output_dir / f"{source.stem}_candidate.braw"


def validate_candidate_path(source: Path, candidate: Path) -> None:
    if source.resolve() == candidate.resolve():
        raise ValueError("candidate path is the same as the source")


def analyze_source(source: Path, output_dir: Path) -> dict:
    return _write_analysis_reports(source, output_dir)


def recover_source(source: Path, candidate: Path, report_dir: Path) -> dict:
    validate_candidate_path(source, candidate)
    if report_dir.resolve() != candidate.parent.resolve():
        raise ValueError("report directory must match the candidate parent directory")
    _repair(source, candidate, report_dir)
    return {"candidate": str(candidate.resolve()), "report_dir": str(report_dir.resolve())}


def verify_candidate(candidate: Path, output_dir: Path) -> dict:
    if output_dir.resolve() != candidate.parent.resolve():
        raise ValueError("report directory must match the candidate parent directory")
    _verify(candidate, output_dir)
    return {"candidate": str(candidate.resolve()), "report_dir": str(output_dir.resolve())}
