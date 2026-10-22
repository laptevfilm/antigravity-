from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brawrec.recovery.scan import HiddenFrame


_SCAN_CHUNK_SIZE = 1024 * 1024
_MDAT_HEADER_SIZE = 16


@dataclass(frozen=True)
class ServiceGap:
    kind: str
    start: int
    end: int
    first_nonzero: int | None
    aligned_offset: int | None


def contains_service_range(gaps: list[ServiceGap], start: int, end: int) -> bool:
    """Return whether an explicit service byte range lies in one known gap."""
    return start >= _MDAT_HEADER_SIZE and any(
        gap.start >= _MDAT_HEADER_SIZE and gap.start <= start and end <= gap.end
        for gap in gaps
    )


def classify_service_gaps(
    path: Path, frames: list[HiddenFrame], moov_offset: int
) -> list[ServiceGap]:
    """Classify bytes between validated hidden frames and the ``moov`` box."""
    boundaries = [
        (frame.offset + frame.size, next_frame.offset)
        for frame, next_frame in zip(frames, frames[1:])
    ]
    if frames:
        boundaries.append((frames[-1].offset + frames[-1].size, moov_offset))

    gaps: list[ServiceGap] = []
    with path.open("rb") as source:
        for start, end in boundaries:
            if end < start:
                raise ValueError("service gap boundaries overlap")
            first_nonzero = _first_nonzero(source, start, end)
            gaps.append(
                ServiceGap(
                    kind=_classify_length(end - start),
                    start=start,
                    end=end,
                    first_nonzero=first_nonzero,
                    aligned_offset=(
                        None
                        if first_nonzero is None
                        else _floor_align(first_nonzero, 256)
                    ),
                )
            )
    return gaps


def _classify_length(length: int) -> str:
    if length < 30_000:
        return "small"
    if length < 80_000:
        return "medium"
    if 250_000 <= length < 400_000:
        return "large"
    return "unknown"


def _floor_align(value: int, alignment: int) -> int:
    return value - value % alignment


def _first_nonzero(source, start: int, end: int) -> int | None:
    source.seek(start)
    offset = start
    while offset < end:
        data = source.read(min(_SCAN_CHUNK_SIZE, end - offset))
        if not data:
            raise ValueError("source ended before service gap boundary")
        for index, value in enumerate(data):
            if value:
                return offset + index
        offset += len(data)
    return None
