from __future__ import annotations

from dataclasses import dataclass

from brawrec.bmff.boxes import u32
from brawrec.braw.tables import BrawLayout, visible_indexed_video_end


FRAME_PATTERN = b"\x00\x00\x01\x00bmdf\x00\x00\x00\x10srte"
_CHUNK_SIZE = 64 * 1024 * 1024
_FRAME_HEADER_SIZE = 256
_FRAME_SIZE_FIELD_SIZE = 8


@dataclass(frozen=True)
class HiddenFrame:
    offset: int
    size: int


def scan_hidden_video(layout: BrawLayout, start: int | None = None) -> list[HiddenFrame]:
    """Find fully validated BRAW frames between the indexed media and ``moov``."""
    media_end = layout.moov_offset
    scan_start = visible_indexed_video_end(layout) if start is None else start
    if not 0 <= scan_start <= media_end:
        raise ValueError("hidden video scan start is outside mdat")

    offsets = _find_frame_offsets(layout, scan_start, media_end)
    return _validate_frames(layout, offsets, media_end)


def _find_frame_offsets(layout: BrawLayout, start: int, end: int) -> list[int]:
    offsets: list[int] = []
    overlap = len(FRAME_PATTERN) - 1
    previous = b""

    with layout.path.open("rb") as source:
        source.seek(start)
        base = start
        while base < end:
            to_read = min(_CHUNK_SIZE, end - base)
            current = source.read(to_read)
            if not current:
                raise ValueError("source ended before mdat boundary")

            window = previous + current
            window_start = base - len(previous)
            position = 0
            while True:
                position = window.find(FRAME_PATTERN, position)
                if position < 0:
                    break
                offsets.append(window_start + position)
                position += 1

            base += len(current)
            previous = window[-overlap:]

    return offsets


def _validate_frames(layout: BrawLayout, offsets: list[int], media_end: int) -> list[HiddenFrame]:
    frames: list[HiddenFrame] = []
    with layout.path.open("rb") as source:
        for index, offset in enumerate(offsets):
            next_limit = offsets[index + 1] if index + 1 < len(offsets) else media_end
            if offset + _FRAME_HEADER_SIZE > next_limit:
                raise ValueError(f"hidden frame overlaps next data at {offset}")

            source.seek(offset + _FRAME_HEADER_SIZE)
            marker = source.read(8)
            if len(marker) != 8 or marker[:4] != b"braw":
                raise ValueError(f"missing braw marker at {offset + _FRAME_HEADER_SIZE}")

            payload_size = u32(marker, 4)
            if payload_size < _FRAME_SIZE_FIELD_SIZE:
                raise ValueError(f"hidden frame payload is too small at {offset}")

            size = _FRAME_HEADER_SIZE + payload_size
            if offset + size > next_limit:
                raise ValueError(f"hidden frame overlaps next data at {offset}")
            frames.append(HiddenFrame(offset=offset, size=size))

    return frames
