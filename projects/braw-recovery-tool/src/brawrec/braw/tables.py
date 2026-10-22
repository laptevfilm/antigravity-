from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from brawrec.bmff.boxes import Box, iter_boxes, u32, u64, walk_boxes

BRAW_VIDEO_SAMPLE_TYPES = {"braw", "brxq"}


@dataclass(frozen=True)
class TrackSummary:
    track_id: int
    sample_type: str | None
    timescale: int | None
    tkhd_duration: int | None
    mdhd_duration: int | None
    stts: list[tuple[int, int]]
    sizes: list[int]
    offsets: list[int]


@dataclass(frozen=True)
class BrawLayout:
    path: Path
    mdat_size: int
    moov_offset: int
    moov_size: int
    tracks: dict[int, TrackSummary]
    trailing_size: int
    moov: bytes


def parse_braw_layout(path: Path) -> BrawLayout:
    with path.open("rb") as source:
        head = source.read(16)
        if len(head) < 16 or head[4:8] != b"mdat":
            raise ValueError("expected mdat-first BRAW")
        mdat_size = u64(head, 8) if u32(head, 0) == 1 else u32(head, 0)
        source.seek(mdat_size)
        moov_head = source.read(8)
        if len(moov_head) < 8 or moov_head[4:8] != b"moov":
            raise ValueError("moov not found at mdat end")
        moov_size = u32(moov_head, 0)
        source.seek(mdat_size)
        moov = source.read(moov_size)
        source.seek(0, 2)
        file_size = source.tell()

    try:
        tracks = _parse_tracks(moov)
    except (IndexError, struct.error) as exc:
        raise ValueError(f"malformed BRAW layout: {exc}") from exc

    return BrawLayout(
        path=path,
        mdat_size=mdat_size,
        moov_offset=mdat_size,
        moov_size=moov_size,
        tracks=tracks,
        trailing_size=file_size - mdat_size - moov_size,
        moov=moov,
    )


def _parse_tracks(moov: bytes) -> dict[int, TrackSummary]:
    tracks: dict[int, TrackSummary] = {}
    for box in iter_boxes(moov, 0, len(moov)):
        if box.type != "moov":
            continue
        for child in iter_boxes(moov, box.body_offset, box.end_offset):
            if child.type != "trak":
                continue
            track_box = Box(child.offset, child.size, child.header_size, child.type, "moov/trak")
            track = _parse_track(moov, track_box)
            tracks[track.track_id] = track
    return tracks


def _parse_track(data: bytes, track_box: Box) -> TrackSummary:
    track_id: int | None = None
    sample_type: str | None = None
    timescale: int | None = None
    tkhd_duration: int | None = None
    mdhd_duration: int | None = None
    stts: list[tuple[int, int]] = []
    sizes: list[int] = []
    offsets: list[int] = []

    for box in walk_boxes(data, track_box.body_offset, track_box.end_offset, track_box.path):
        body = box.body_offset
        if box.type == "tkhd":
            version = data[body]
            track_id = u32(data, body + (20 if version else 12))
            tkhd_duration = u64(data, body + 28) if version else u32(data, body + 20)
        elif box.type == "mdhd":
            version = data[body]
            timescale = u32(data, body + (20 if version else 12))
            mdhd_duration = u64(data, body + 24) if version else u32(data, body + 16)
        elif box.type == "stsd" and u32(data, body + 4):
            sample_type = data[body + 12:body + 16].decode("latin-1", "replace")
        elif box.type == "stts":
            stts = _parse_table(data, box)
        elif box.type == "stsz":
            sizes = _parse_stsz(data, box)
        elif box.type in {"stco", "co64"}:
            offsets = _parse_table(data, box)

    if track_id is None:
        raise ValueError("track missing tkhd track ID")
    return TrackSummary(
        track_id=track_id,
        sample_type=sample_type,
        timescale=timescale,
        tkhd_duration=tkhd_duration,
        mdhd_duration=mdhd_duration,
        stts=stts,
        sizes=sizes,
        offsets=offsets,
    )


def _parse_stsz(data: bytes, box: Box) -> list[int]:
    body = box.body_offset
    sample_size = u32(data, body + 4)
    count = u32(data, body + 8)
    if sample_size:
        return [sample_size] * count
    return [u32(data, body + 12 + index * 4) for index in range(count)]


def _parse_table(data: bytes, box: Box) -> list[tuple[int, int]] | list[int]:
    body = box.body_offset
    count = u32(data, body + 4)
    if box.type == "stts":
        return [
            (u32(data, body + 8 + index * 8), u32(data, body + 12 + index * 8))
            for index in range(count)
        ]
    if box.type == "stco":
        return [u32(data, body + 8 + index * 4) for index in range(count)]
    if box.type == "co64":
        return [u64(data, body + 8 + index * 8) for index in range(count)]
    raise ValueError(f"unsupported table type: {box.type}")


def find_video_track(layout: BrawLayout) -> TrackSummary:
    for track in layout.tracks.values():
        if track.sample_type in BRAW_VIDEO_SAMPLE_TYPES:
            return track
    raise ValueError("BRAW video track not found")


def visible_indexed_video_end(layout: BrawLayout) -> int:
    track = find_video_track(layout)
    if not track.sizes or not track.offsets:
        raise ValueError("BRAW video track has no indexed samples")
    if len(track.sizes) != len(track.offsets):
        raise ValueError("BRAW video track sample sizes and offsets do not match")
    return track.offsets[-1] + track.sizes[-1]
