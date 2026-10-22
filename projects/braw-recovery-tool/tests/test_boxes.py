import pytest

from brawrec.bmff.boxes import iter_boxes, p32, p64, u32, u64, walk_boxes


def box(kind: bytes, body: bytes) -> bytes:
    return p32(8 + len(body)) + kind + body


def test_endian_helpers_round_trip():
    data = p32(25) + p64(123456789)
    assert u32(data, 0) == 25
    assert u64(data, 4) == 123456789


def test_iter_boxes_reads_standard_and_large_sizes():
    regular = box(b"free", b"abc")
    large = p32(1) + b"mdat" + p64(20) + b"xxxx"
    parsed = list(iter_boxes(regular + large, 0, len(regular + large)))
    assert [(b.type, b.size, b.header_size) for b in parsed] == [
        ("free", 11, 8),
        ("mdat", 20, 16),
    ]


def test_walk_boxes_descends_into_moov_trak():
    trak = box(b"trak", box(b"tkhd", b"\0" * 24))
    moov = box(b"moov", trak)
    paths = [b.path for b in walk_boxes(moov, 0, len(moov))]
    assert paths == ["moov", "moov/trak", "moov/trak/tkhd"]


def test_iter_boxes_rejects_invalid_size():
    with pytest.raises(ValueError, match="invalid box"):
        list(iter_boxes(p32(4) + b"free", 0, 8))
