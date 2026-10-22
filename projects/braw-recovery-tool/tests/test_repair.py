from pathlib import Path

import pytest

from brawrec.bmff.boxes import iter_boxes, u32
from brawrec.braw.tables import parse_braw_layout
from brawrec.recovery import repair
from brawrec.recovery.repair import build_repair_plan, write_candidate
from brawrec.recovery.scan import FRAME_PATTERN, HiddenFrame
from tests.fixtures import box, synthetic_braw, trak


def frame(payload_size: int) -> bytes:
    data = bytearray(256 + payload_size)
    data[: len(FRAME_PATTERN)] = FRAME_PATTERN
    data[256:260] = b"braw"
    data[260:264] = payload_size.to_bytes(4, "big")
    return bytes(data)


def source_with_hidden_frame(
    tmp_path: Path,
    *,
    offset: int = 512,
    payload_size: int = 300,
    **track_options: object,
) -> tuple[Path, HiddenFrame]:
    source = tmp_path / "clip.braw"
    if "movie_timescale" not in track_options:
        track_options["movie_timescale"] = 25
        track_options["movie_duration"] = 1
    payload = bytearray(synthetic_braw([100], [256], 2048, **track_options))
    hidden = frame(payload_size)
    payload[offset : offset + len(hidden)] = hidden
    source.write_bytes(bytes(payload))
    return source, HiddenFrame(offset=offset, size=len(hidden))


def test_build_repair_plan_rejects_source_output_conflict(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    layout = parse_braw_layout(source)

    with pytest.raises(ValueError, match="same as source"):
        build_repair_plan(layout, source, [HiddenFrame(offset=512, size=556)])


def test_build_repair_plan_counts_final_video_frames(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path)
    layout = parse_braw_layout(source)
    output = tmp_path / "candidate.braw"

    plan = build_repair_plan(layout, output, [hidden])

    assert plan.final_video_frames == 2
    assert plan.video_track_id == 1
    assert plan.confidence == "high"


def test_write_candidate_preserves_source_and_writes_output(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path)
    original = source.read_bytes()
    layout = parse_braw_layout(source)
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(layout, output, [hidden])

    write_candidate(plan)

    assert source.read_bytes() == original
    assert output.exists()
    assert output.stat().st_size >= source.stat().st_size
    candidate = parse_braw_layout(output)
    assert candidate.tracks[1].sizes == [100, 556]
    assert candidate.tracks[1].offsets == [256, 512]
    assert candidate.tracks[1].stts == [(2, 1)]
    assert output.read_bytes()[-4:] == b"tail"


def test_write_candidate_preserves_non_box_moov_meta_payload(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path)
    payload = source.read_bytes()
    moov_offset = 2048
    moov_size = u32(payload, moov_offset)
    moov = payload[moov_offset : moov_offset + moov_size]
    opaque_meta = box(b"meta", b"\0\0\0\0not-a-box-stream")
    source.write_bytes(payload[:moov_offset] + box(b"moov", moov[8:] + opaque_meta) + b"tail")
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(parse_braw_layout(source), output, [hidden])

    write_candidate(plan)

    assert opaque_meta in output.read_bytes()
    assert parse_braw_layout(output).tracks[1].sizes == [100, 556]


def test_write_candidate_removes_partial_output_when_copy_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source, hidden = source_with_hidden_frame(tmp_path)
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(parse_braw_layout(source), output, [hidden])

    def fail_copy(*_args, **_kwargs) -> None:
        raise OSError("simulated copy failure")

    monkeypatch.setattr(repair, "_copy_exact", fail_copy)

    with pytest.raises(OSError, match="simulated copy failure"):
        write_candidate(plan)

    assert not output.exists()


def test_build_repair_plan_rejects_fake_hidden_frame_in_zero_bytes(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))

    with pytest.raises(ValueError, match="frame pattern"):
        build_repair_plan(
            parse_braw_layout(source), tmp_path / "candidate.braw", [HiddenFrame(offset=512, size=556)]
        )


def test_build_repair_plan_rejects_hidden_frame_overlapping_indexed_sample(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, offset=300)

    with pytest.raises(ValueError, match="indexed video sample"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_hidden_frame_overlapping_non_video_track(tmp_path: Path):
    source, hidden = source_with_hidden_frame(
        tmp_path,
        extra_tracks=[trak(2, b"sowt", [200], [512])],
    )

    with pytest.raises(ValueError, match="indexed track sample"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_offset_heavy_non_video_track(tmp_path: Path):
    source, hidden = source_with_hidden_frame(
        tmp_path,
        extra_tracks=[trak(2, b"sowt", [200], [512, 768])],
    )

    with pytest.raises(ValueError, match="indexed track sample sizes and offsets do not match"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_size_heavy_non_video_track(tmp_path: Path):
    source, hidden = source_with_hidden_frame(
        tmp_path,
        extra_tracks=[trak(2, b"sowt", [200, 300], [512])],
    )

    with pytest.raises(ValueError, match="indexed track sample sizes and offsets do not match"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_payload_size_mismatch(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path)
    mismatched = HiddenFrame(offset=hidden.offset, size=hidden.size - 1)

    with pytest.raises(ValueError, match="size"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [mismatched])


def test_build_repair_plan_rejects_fixed_size_stsz_mismatch(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, fixed_size=100)

    with pytest.raises(ValueError, match="fixed-size stsz"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_missing_mvhd_with_mismatched_track_durations(tmp_path: Path):
    source, hidden = source_with_hidden_frame(
        tmp_path, tkhd_duration=40, movie_timescale=None
    )

    with pytest.raises(ValueError, match="mvhd"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_missing_mvhd_even_when_durations_match(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, movie_timescale=None)

    with pytest.raises(ValueError, match="mvhd"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_stco_video_offsets(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, offset_table="stco")

    with pytest.raises(ValueError, match="stco"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_rejects_stts_count_mismatch(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, stts_count=2)

    with pytest.raises(ValueError, match="stts sample count"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_write_candidate_updates_version_one_track_fields(tmp_path: Path):
    source, hidden = source_with_hidden_frame(tmp_path, version=1)
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(parse_braw_layout(source), output, [hidden])

    write_candidate(plan)

    track = parse_braw_layout(output).tracks[1]
    assert track.tkhd_duration == 2
    assert track.mdhd_duration == 2


def test_write_candidate_converts_and_updates_movie_duration(tmp_path: Path):
    source, hidden = source_with_hidden_frame(
        tmp_path, movie_timescale=1000, movie_duration=40, tkhd_duration=40
    )
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(parse_braw_layout(source), output, [hidden])

    write_candidate(plan)

    candidate = parse_braw_layout(output)
    assert candidate.tracks[1].mdhd_duration == 2
    assert candidate.tracks[1].tkhd_duration == 80
    mvhd = next(box for box in iter_boxes(candidate.moov, 0, len(candidate.moov)) if box.type == "moov")
    movie_header = next(
        box for box in iter_boxes(candidate.moov, mvhd.body_offset, mvhd.end_offset) if box.type == "mvhd"
    )
    assert u32(candidate.moov, movie_header.body_offset + 16) == 80


@pytest.mark.parametrize("entries", [0, 2])
def test_build_repair_plan_rejects_unsupported_edit_list_shape(tmp_path: Path, entries: int):
    source, hidden = source_with_hidden_frame(tmp_path, elst_entries=entries)

    with pytest.raises(ValueError, match="one entry"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


@pytest.mark.parametrize(
    ("track_options", "message"),
    [
        ({"elst_entries": 1, "elst_media_time": 1}, "media_time"),
        ({"elst_entries": 1, "elst_rate_integer": 0}, "rate"),
        ({"elst_entries": 1, "elst_rate_fraction": 1}, "rate"),
        ({"elst_entries": 1, "elst_media_time": 1, "version": 1}, "media_time"),
    ],
)
def test_build_repair_plan_rejects_unsupported_one_entry_edit_list(
    tmp_path: Path, track_options: dict[str, int], message: str
):
    source, hidden = source_with_hidden_frame(tmp_path, **track_options)

    with pytest.raises(ValueError, match=message):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])
