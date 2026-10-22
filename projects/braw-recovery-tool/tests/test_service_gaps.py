from pathlib import Path

from brawrec.recovery.scan import HiddenFrame
from brawrec.recovery.service_gaps import ServiceGap, classify_service_gaps, contains_service_range


def test_classify_medium_and_large_nonzero_gaps(tmp_path: Path):
    path = tmp_path / "clip.braw"
    data = bytearray(2_000_000)
    data[600_123] = 1
    data[1_200_123] = 1
    path.write_bytes(bytes(data))

    frames = [
        HiddenFrame(offset=100_000, size=250_000),
        HiddenFrame(offset=650_000, size=550_000),
        HiddenFrame(offset=1_550_000, size=100_000),
    ]

    gaps = classify_service_gaps(path, frames, moov_offset=1_900_000)

    assert [g.kind for g in gaps[:2]] == ["large", "large"]
    assert gaps[0].aligned_offset == 600_064
    assert gaps[1].aligned_offset == 1_199_872


def test_classify_thresholds_and_zero_gap_data(tmp_path: Path):
    path = tmp_path / "clip.braw"
    data = bytearray(500_000)
    data[50_123] = 1
    data[100_123] = 1
    data[300_123] = 1
    path.write_bytes(bytes(data))

    frames = [
        HiddenFrame(offset=0, size=10_000),
        HiddenFrame(offset=20_000, size=10_000),
        HiddenFrame(offset=80_000, size=10_000),
        HiddenFrame(offset=340_000, size=10_000),
    ]

    gaps = classify_service_gaps(path, frames, moov_offset=500_000)

    assert [gap.kind for gap in gaps] == ["small", "medium", "large", "unknown"]
    assert gaps[0].first_nonzero is None
    assert gaps[0].aligned_offset is None
    assert gaps[1].first_nonzero == 50_123
    assert gaps[1].aligned_offset == 49_920


def test_service_range_excludes_initial_mdat_header():
    gap = ServiceGap("large", 0, 500_000, 16, None)

    assert not contains_service_range([gap], 12, 16)
