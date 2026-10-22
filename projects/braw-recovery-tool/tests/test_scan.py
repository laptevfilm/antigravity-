from pathlib import Path

import pytest

from brawrec.braw.tables import parse_braw_layout
from brawrec.recovery.scan import FRAME_PATTERN, scan_hidden_video
from tests.fixtures import synthetic_braw


def frame(payload_size: int) -> bytes:
    data = bytearray(256 + payload_size)
    data[: len(FRAME_PATTERN)] = FRAME_PATTERN
    data[256:260] = b"braw"
    data[260:264] = payload_size.to_bytes(4, "big")
    return bytes(data)


def test_scan_hidden_video_finds_valid_non_overlapping_frames(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    hidden = frame(300)
    payload[512 : 512 + len(hidden)] = hidden
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)
    frames = scan_hidden_video(layout, start=512)

    assert [(item.offset, item.size) for item in frames] == [(512, 556)]


def test_scan_hidden_video_rejects_overlap(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    first = frame(800)
    second = frame(100)
    payload[512 : 512 + len(first)] = first
    payload[700 : 700 + len(second)] = second
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)
    with pytest.raises(ValueError, match="overlaps"):
        scan_hidden_video(layout, start=512)


def test_scan_hidden_video_starts_after_visible_index_when_start_is_omitted(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    hidden = frame(300)
    payload[356 : 356 + len(hidden)] = hidden
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)

    assert [(item.offset, item.size) for item in scan_hidden_video(layout)] == [(356, 556)]


@pytest.mark.parametrize("payload_size", range(8))
def test_scan_hidden_video_rejects_payload_smaller_than_declared_size_field(
    tmp_path: Path, payload_size: int
):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    hidden = frame(payload_size)
    payload[512 : 512 + len(hidden)] = hidden
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)

    with pytest.raises(ValueError, match="payload"):
        scan_hidden_video(layout, start=512)
