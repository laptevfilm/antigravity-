from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator
import struct


CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "tref", "dinf", "udta", "meta"}


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def u64(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">Q", data, offset)[0]


def p32(value: int) -> bytes:
    return struct.pack(">I", value)


def p64(value: int) -> bytes:
    return struct.pack(">Q", value)


@dataclass(frozen=True)
class Box:
    offset: int
    size: int
    header_size: int
    type: str
    path: str

    @property
    def body_offset(self) -> int:
        return self.offset + self.header_size

    @property
    def end_offset(self) -> int:
        return self.offset + self.size


def iter_boxes(data: bytes | bytearray, start: int, end: int) -> Iterator[Box]:
    pos = start
    while pos + 8 <= end:
        size = u32(data, pos)
        kind = data[pos + 4:pos + 8].decode("latin-1", "replace")
        header_size = 8
        if size == 1:
            if pos + 16 > end:
                raise ValueError(f"invalid box {kind!r} at {pos}: missing 64-bit size")
            size = u64(data, pos + 8)
            header_size = 16
        elif size == 0:
            size = end - pos
        if size < header_size or pos + size > end:
            raise ValueError(f"invalid box {kind!r} at {pos}, size {size}")
        yield Box(pos, size, header_size, kind, kind)
        pos += size
    if pos != end:
        raise ValueError(f"box parse stopped at {pos}, expected {end}")


def walk_boxes(data: bytes | bytearray, start: int, end: int, path: str = "") -> Iterator[Box]:
    for box in iter_boxes(data, start, end):
        cur_path = f"{path}/{box.type}" if path else box.type
        current = Box(box.offset, box.size, box.header_size, box.type, cur_path)
        yield current
        child_start = box.body_offset + (4 if box.type == "meta" else 0)
        if box.type in CONTAINERS and child_start < box.end_offset:
            yield from walk_boxes(data, child_start, box.end_offset, cur_path)
