from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path, PurePosixPath
import sys

from brawrec.braw.tables import TrackSummary, parse_braw_layout, visible_indexed_video_end
from brawrec.filesystem.hfs import extract_braw_file, inventory_braw_files
from brawrec.recovery.repair import build_repair_plan, write_candidate
from brawrec.recovery.scan import HiddenFrame, scan_hidden_video
from brawrec.recovery.service_gaps import classify_service_gaps
from brawrec.reports import write_json_report, write_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brawrec")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("card_image")

    extract = sub.add_parser("extract")
    extract.add_argument("card_image")
    extract.add_argument("--clip", required=True)
    extract.add_argument("--out", required=True)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("source")
    analyze.add_argument("--out", default=".")

    repair = sub.add_parser("repair")
    repair.add_argument("source")
    repair.add_argument("--out", required=True)
    repair.add_argument("--report", default=".")

    verify = sub.add_parser("verify")
    verify.add_argument("candidate")
    verify.add_argument("--out", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "inventory":
            files = inventory_braw_files(Path(args.card_image))
            print(json.dumps({"braw_count": len(files), "braws": [asdict(file) for file in files]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "extract":
            files = inventory_braw_files(Path(args.card_image))
            target = _find_hfs_file(files, args.clip)
            if target is None:
                raise ValueError(f"BRAW clip not found: {args.clip}")
            print(extract_braw_file(Path(args.card_image), target, Path(args.out)))
            return 0
        if args.command == "analyze":
            _write_analysis_reports(Path(args.source), Path(args.out))
            return 0
        if args.command == "repair":
            _repair(Path(args.source), Path(args.out), Path(args.report))
            return 0
        if args.command == "verify":
            _verify(Path(args.candidate), Path(args.out))
            return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 2


def console_main() -> None:
    raise SystemExit(main())


def _find_hfs_file(files, clip: str):
    normalized = clip.replace("\\", "/")
    exact_matches = [file for file in files if clip == str(file.id) or normalized == file.path]
    if exact_matches:
        return exact_matches[0]
    basename_matches = [file for file in files if normalized == PurePosixPath(file.path).name]
    if len(basename_matches) == 1:
        return basename_matches[0]
    if basename_matches:
        raise ValueError(f"ambiguous BRAW clip name: {clip}; use full HFS path or catalog ID")
    return None


def _write_analysis_reports(source: Path, report_dir: Path) -> dict:
    payload = _analyze(source)
    write_json_report(report_dir / "analysis.json", payload)
    write_markdown_report(report_dir / "analysis.md", "Analysis", payload)
    return payload


def _analyze(source: Path) -> dict:
    layout = parse_braw_layout(source)
    visible_end = visible_indexed_video_end(layout)
    hidden_frames = scan_hidden_video(layout, start=visible_end)
    service_gaps = classify_service_gaps(layout.path, hidden_frames, layout.moov_offset)
    return {
        "source": str(layout.path.resolve()),
        "mdat_size": layout.mdat_size,
        "moov_offset": layout.moov_offset,
        "moov_size": layout.moov_size,
        "trailing_size": layout.trailing_size,
        "visible_video_end": visible_end,
        "tracks": [_track_payload(track) for track in layout.tracks.values()],
        "hidden_frames": [asdict(frame) for frame in hidden_frames],
        "service_gaps": [asdict(gap) for gap in service_gaps],
    }


def _repair(source: Path, output: Path, report_dir: Path) -> None:
    hidden_frames: list[HiddenFrame] | None = None
    try:
        layout = parse_braw_layout(source)
        visible_end = visible_indexed_video_end(layout)
        hidden_frames = scan_hidden_video(layout, start=visible_end)
        plan = build_repair_plan(layout, output, hidden_frames)
        write_candidate(plan)
    except (OSError, ValueError) as exc:
        _write_repair_refusal_reports(report_dir, source, output, hidden_frames, str(exc))
        raise
    payload = {
        "source": str(plan.source),
        "candidate": str(plan.output),
        "hidden_frames": [asdict(frame) for frame in plan.hidden_frames],
        "video_track_id": plan.video_track_id,
        "final_video_frames": plan.final_video_frames,
        "confidence": plan.confidence,
    }
    write_json_report(report_dir / "repair.json", payload)
    write_markdown_report(report_dir / "repair.md", "Repair", payload)


def _write_repair_refusal_reports(
    report_dir: Path,
    source: Path,
    output: Path,
    hidden_frames: list[HiddenFrame] | None,
    refusal_reason: str,
) -> None:
    payload = {
        "status": "refused",
        "refusal_reason": refusal_reason,
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "hidden_frame_count": len(hidden_frames) if hidden_frames is not None else None,
        "confidence": "not_assessed",
    }
    write_json_report(report_dir / "repair.json", payload)
    write_markdown_report(report_dir / "repair.md", "Repair", payload)


def _verify(candidate: Path, report_dir: Path) -> None:
    layout = parse_braw_layout(candidate)
    payload = {
        "candidate": str(layout.path.resolve()),
        "track_count": len(layout.tracks),
        "tracks": [_track_payload(track) for track in layout.tracks.values()],
    }
    write_json_report(report_dir / "verify.json", payload)
    write_markdown_report(report_dir / "verify.md", "Verification", payload)


def _track_payload(track: TrackSummary) -> dict:
    return {
        "track_id": track.track_id,
        "sample_type": track.sample_type,
        "sample_count": len(track.sizes),
        "timescale": track.timescale,
        "tkhd_duration": track.tkhd_duration,
        "mdhd_duration": track.mdhd_duration,
    }
