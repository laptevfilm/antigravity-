from pathlib import Path

from brawrec.braw.tables import find_video_track, parse_braw_layout, visible_indexed_video_end
from tests.fixtures import box, synthetic_braw


def test_parse_braw_layout_reads_mdat_moov_and_track_tables(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100, 120], [256, 512], 2048))

    layout = parse_braw_layout(source)

    assert layout.mdat_size == 2048
    assert layout.moov_offset == 2048
    assert layout.trailing_size == 4
    track = layout.tracks[1]
    assert track.sample_type == "braw"
    assert track.sizes == [100, 120]
    assert track.offsets == [256, 512]
    assert track.stts == [(2, 1)]


def test_visible_indexed_video_end_uses_last_offset_plus_size(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100, 120], [256, 512], 2048))

    layout = parse_braw_layout(source)

    assert find_video_track(layout).track_id == 1
    assert visible_indexed_video_end(layout) == 632


def test_parse_braw_layout_reads_version_one_track_fields(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048, version=1))

    track = parse_braw_layout(source).tracks[1]

    assert track.track_id == 1
    assert track.tkhd_duration == 1
    assert track.timescale == 25
    assert track.mdhd_duration == 1


def test_parse_braw_layout_ignores_non_track_moov_payload_siblings(tmp_path: Path):
    source = tmp_path / "clip.braw"
    base = synthetic_braw([100], [256], 2048)
    moov_offset = 2048
    moov_size = int.from_bytes(base[moov_offset : moov_offset + 4], "big")
    moov_body = base[moov_offset + 8 : moov_offset + moov_size]
    bad_meta = box(b"meta", b"not-a-box-stream")
    moov = box(b"moov", moov_body + bad_meta)
    source.write_bytes(base[:moov_offset] + moov + b"tail")

    layout = parse_braw_layout(source)

    assert layout.tracks[1].sample_type == "braw"


def test_find_video_track_accepts_real_braw_video_sample_entry(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048, sample_type=b"brxq"))

    layout = parse_braw_layout(source)

    assert find_video_track(layout).track_id == 1
