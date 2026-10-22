from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import tempfile

from brawrec.bmff.boxes import CONTAINERS, Box, iter_boxes, p32, p64, u32, u64
from brawrec.braw.tables import BrawLayout, TrackSummary, find_video_track, parse_braw_layout
from brawrec.recovery.scan import FRAME_PATTERN, HiddenFrame
from brawrec.recovery.service_gaps import ServiceGap, contains_service_range


@dataclass(frozen=True)
class RepairPlan:
    source: Path
    output: Path
    hidden_frames: list[HiddenFrame]
    video_track_id: int
    final_video_frames: int
    confidence: str
    service_patches: dict[int, ServicePatch] = field(default_factory=dict)
    service_gaps: list[ServiceGap] = field(default_factory=list)


@dataclass(frozen=True)
class ServicePatch:
    """Explicitly validated samples to append to one non-video service track."""

    track_id: int
    offsets: list[int]
    added_samples: int


@dataclass(frozen=True)
class TrackRepairPatch:
    track_id: int
    sizes: list[int]
    offsets: list[int]
    sample_count: int
    media_duration: int
    movie_duration: int


@dataclass(frozen=True)
class MovieTiming:
    timescale: int
    duration: int

def build_repair_plan(
    layout: BrawLayout,
    output: Path,
    hidden_frames: list[HiddenFrame],
    *,
    service_patches: dict[int, ServicePatch] | None = None,
    service_gaps: list[ServiceGap] | None = None,
) -> RepairPlan:
    """Create a candidate repair plan from validated video and service samples."""
    source = layout.path.resolve()
    destination = output.resolve()
    if source == destination:
        raise ValueError("output path is the same as source")
    if not hidden_frames:
        raise ValueError("no hidden frames to repair")

    video_track = find_video_track(layout)
    frames = sorted(hidden_frames, key=lambda frame: frame.offset)
    _validate_hidden_frames(layout, frames, video_track)
    _validate_video_track_structure(layout.moov, video_track)
    media_duration = _media_duration(video_track, len(video_track.sizes) + len(frames))
    _movie_duration(video_track, media_duration, _movie_timing(layout.moov))
    _validate_fixed_stsz(layout.moov, video_track, frames)
    patches = dict(service_patches or {})
    _validate_service_patches(layout, video_track, frames, patches, service_gaps)
    return RepairPlan(
        source=source,
        output=destination,
        hidden_frames=frames,
        video_track_id=video_track.track_id,
        final_video_frames=len(video_track.sizes) + len(frames),
        confidence="high",
        service_patches=patches,
        service_gaps=list(service_gaps or []),
    )


def _validate_hidden_frames(
    layout: BrawLayout, frames: list[HiddenFrame], video_track: TrackSummary
) -> None:
    previous_end = None
    if len(video_track.sizes) != len(video_track.offsets):
        raise ValueError("indexed video sample sizes and offsets do not match")
    indexed_ranges = {
        track.track_id: _indexed_track_ranges(
            layout.moov,
            track,
            "video track" if track.track_id == video_track.track_id else "non-video track",
        )
        for track in layout.tracks.values()
    }

    with layout.path.open("rb") as source:
        for frame in frames:
            if frame.size <= 0:
                raise ValueError("hidden frame size must be nonempty")
            if not 0 <= frame.offset < layout.moov_offset:
                raise ValueError("hidden frame is outside mdat")
            frame_end = frame.offset + frame.size
            if frame_end > layout.moov_offset:
                raise ValueError("hidden frame extends outside mdat")
            if previous_end is not None and frame.offset < previous_end:
                raise ValueError("hidden frames overlap")
            for track in layout.tracks.values():
                if any(
                    frame.offset < sample_start + sample_size and sample_start < frame_end
                    for sample_start, sample_size in indexed_ranges[track.track_id]
                ):
                    sample_kind = "video sample" if track.track_id == video_track.track_id else "track sample"
                    raise ValueError(f"hidden frame overlaps indexed {sample_kind}")

            source.seek(frame.offset)
            if source.read(len(FRAME_PATTERN)) != FRAME_PATTERN:
                raise ValueError("hidden frame pattern is missing at declared offset")
            source.seek(frame.offset + 256)
            marker = source.read(8)
            if len(marker) != 8 or marker[:4] != b"braw":
                raise ValueError("hidden frame braw marker is missing")
            payload_size = u32(marker, 4)
            if payload_size < 8:
                raise ValueError("hidden frame payload is too small")
            if 256 + payload_size != frame.size:
                raise ValueError("hidden frame size does not match encoded payload")
            previous_end = frame_end


def write_candidate(plan: RepairPlan) -> None:
    """Write a new video-index repair candidate without modifying its source."""
    source = plan.source.resolve()
    output = plan.output.resolve()
    if source == output:
        raise ValueError("output path is the same as source")
    if plan.confidence != "high":
        raise ValueError("repair plan confidence is too low to write a candidate")

    layout = parse_braw_layout(source)
    frames = sorted(plan.hidden_frames, key=lambda frame: frame.offset)
    video_track = find_video_track(layout)
    _validate_hidden_frames(layout, frames, video_track)
    _validate_video_track_structure(layout.moov, video_track)
    _validate_fixed_stsz(layout.moov, video_track, frames)
    if video_track.track_id != plan.video_track_id:
        raise ValueError("repair plan video track does not match source")

    movie_timing = _movie_timing(layout.moov)
    patch = _video_patch(video_track, frames, plan.final_video_frames, movie_timing)
    _validate_service_patches(
        layout, video_track, frames, plan.service_patches, plan.service_gaps
    )
    service_tracks = {
        track_id: _service_track_patch(
            layout.moov, layout.tracks[track_id], service_patch, movie_timing
        )
        for track_id, service_patch in plan.service_patches.items()
    }
    patches = _CandidatePatches(
        video=patch,
        movie_duration=max(
            movie_timing.duration,
            patch.movie_duration,
            *(service_patch.movie_duration for service_patch in service_tracks.values()),
        ),
        service_tracks=service_tracks,
    )
    rebuilt_moov = _rebuild_box(layout.moov, patches)
    _copy_candidate(layout, source, output, rebuilt_moov)


@dataclass(frozen=True)
class _CandidatePatches:
    video: TrackRepairPatch
    movie_duration: int | None
    service_tracks: dict[int, TrackRepairPatch]


def _video_patch(
    track: TrackSummary,
    frames: list[HiddenFrame],
    final_video_frames: int,
    movie_timing: MovieTiming | None,
) -> TrackRepairPatch:
    sizes = track.sizes + [frame.size for frame in frames]
    offsets = track.offsets + [frame.offset for frame in frames]
    if len(sizes) != final_video_frames:
        raise ValueError("repair plan frame count does not match source")
    media_duration = _media_duration(track, final_video_frames)
    movie_duration = _movie_duration(track, media_duration, movie_timing)
    return TrackRepairPatch(
        track_id=track.track_id,
        sizes=sizes,
        offsets=offsets,
        sample_count=final_video_frames,
        media_duration=media_duration,
        movie_duration=movie_duration,
    )


def _service_track_patch(
    moov: bytes, track: TrackSummary, service_patch: ServicePatch, movie_timing: MovieTiming
) -> TrackRepairPatch:
    final_samples = len(track.sizes) + service_patch.added_samples
    fixed_size = _fixed_stsz_size_for_track(moov, track)
    media_duration = _track_media_duration(track, final_samples, "service track")
    return TrackRepairPatch(
        track_id=track.track_id,
        sizes=track.sizes + [fixed_size] * service_patch.added_samples,
        offsets=track.offsets + service_patch.offsets,
        sample_count=final_samples,
        media_duration=media_duration,
        movie_duration=_movie_duration(track, media_duration, movie_timing, "service track"),
    )


def _media_duration(track: TrackSummary, sample_count: int) -> int:
    return _track_media_duration(track, sample_count, "video track")


def _track_media_duration(track: TrackSummary, sample_count: int, track_kind: str) -> int:
    if len(track.stts) != 1:
        raise ValueError(f"{track_kind} stts must have one entry for MVP repair")
    if track.stts[0][0] != len(track.sizes):
        raise ValueError(f"{track_kind} stts sample count does not match indexed samples")
    return sample_count * track.stts[0][1]


def _movie_timing(moov: bytes) -> MovieTiming:
    movie_headers = [box for box in _moov_children(moov) if box.type == "mvhd"]
    if len(movie_headers) != 1:
        raise ValueError("moov must contain exactly one mvhd for MVP repair")
    header = movie_headers[0]
    version = moov[header.body_offset]
    if version not in {0, 1}:
        raise ValueError("mvhd version is unsupported for MVP repair")
    timescale_offset = header.body_offset + (20 if version else 12)
    duration_offset = header.body_offset + (24 if version else 16)
    duration = u64(moov, duration_offset) if version else u32(moov, duration_offset)
    return MovieTiming(timescale=u32(moov, timescale_offset), duration=duration)


def _movie_duration(
    track: TrackSummary,
    media_duration: int,
    movie_timing: MovieTiming,
    track_kind: str = "video track",
) -> int:
    if not track.timescale:
        raise ValueError(f"{track_kind} has no media timescale")
    if not movie_timing.timescale:
        raise ValueError("movie timescale must be nonzero")
    scaled_duration = media_duration * movie_timing.timescale
    if scaled_duration % track.timescale:
        raise ValueError(f"{track_kind} duration cannot be represented in movie timescale")
    return scaled_duration // track.timescale


def _validate_video_track_structure(moov: bytes, track: TrackSummary) -> None:
    boxes = _track_boxes(moov, track.track_id)
    offset_boxes = [box for box in boxes if box.type in {"stco", "co64"}]
    if any(box.type == "stco" for box in offset_boxes):
        raise ValueError("video track stco offsets are unsupported for MVP repair")
    if len(offset_boxes) != 1 or offset_boxes[0].type != "co64":
        raise ValueError("video track must contain exactly one co64 offset table for MVP repair")

    edit_lists = [box for box in boxes if box.type == "elst"]
    if len(edit_lists) > 1:
        raise ValueError("video track must contain at most one edit list for MVP repair")
    for edit_list in edit_lists:
        _validate_elst(moov[edit_list.offset:edit_list.end_offset], "video track")


def _validate_service_track_structure(moov: bytes, track: TrackSummary) -> None:
    boxes = _track_boxes(moov, track.track_id)
    offset_boxes = [box for box in boxes if box.type in {"stco", "co64"}]
    if any(box.type == "stco" for box in offset_boxes):
        raise ValueError("service track stco offsets are unsupported for MVP repair")
    if len(offset_boxes) != 1 or offset_boxes[0].type != "co64":
        raise ValueError("service track must contain exactly one co64 offset table for MVP repair")

    edit_lists = [box for box in boxes if box.type == "elst"]
    if len(edit_lists) > 1:
        raise ValueError("service track must contain at most one edit list for MVP repair")
    for edit_list in edit_lists:
        _validate_elst(moov[edit_list.offset:edit_list.end_offset], "service track")


def _track_boxes(moov: bytes, track_id: int):
    for box in _moov_children(moov):
        if box.type != "trak":
            continue
        track_raw = moov[box.offset:box.end_offset]
        if _track_id(track_raw) == track_id:
            return list(_walk_repair_boxes(moov, box.body_offset, box.end_offset, box.path))
    raise ValueError("track is missing from moov")


def _validate_fixed_stsz(moov: bytes, track: TrackSummary, frames: list[HiddenFrame]) -> None:
    fixed_size = _fixed_stsz_size(moov, track.track_id, "video track")
    if fixed_size and any(frame.size != fixed_size for frame in frames):
        raise ValueError("fixed-size stsz cannot represent hidden frame sizes")


def _fixed_stsz_size(moov: bytes, track_id: int, track_kind: str = "track") -> int:
    for box in _moov_children(moov):
        if box.type != "trak":
            continue
        track_raw = moov[box.offset:box.end_offset]
        if _track_id(track_raw) != track_id:
            continue
        for child in _walk_repair_boxes(moov, box.body_offset, box.end_offset, box.path):
            if child.type == "stsz":
                return u32(moov, child.body_offset + 4)
        raise ValueError(f"{track_kind} is missing stsz")
    raise ValueError(f"{track_kind} is missing from moov")


def _fixed_stsz_size_for_track(moov: bytes, track: TrackSummary) -> int:
    if not track.sizes:
        raise ValueError("service track has no indexed samples")
    fixed_size = _fixed_stsz_size(moov, track.track_id, "service track")
    if not fixed_size or any(size != fixed_size for size in track.sizes):
        raise ValueError("service track must use fixed-size stsz for MVP repair")
    return fixed_size


def _indexed_track_ranges(
    moov: bytes, track: TrackSummary, track_kind: str
) -> list[tuple[int, int]]:
    if track_kind == "video track":
        if len(track.offsets) == len(track.sizes):
            return list(zip(track.offsets, track.sizes))
        raise ValueError("indexed video sample sizes and offsets do not match")

    fixed_size = _fixed_stsz_size(moov, track.track_id, track_kind)
    if not fixed_size:
        raise ValueError("indexed track sample sizes and offsets do not match")
    samples_per_chunk = _supported_stsc_samples_per_chunk(
        moov,
        track,
        "non-video track sample mapping (stsc) is unsupported for overlap checks",
    )
    if len(track.sizes) != len(track.offsets) * samples_per_chunk:
        raise ValueError("non-video track sample mapping is unsupported for overlap checks")
    if len(track.offsets) == len(track.sizes):
        return list(zip(track.offsets, track.sizes))
    return [(offset, fixed_size * samples_per_chunk) for offset in track.offsets]


def _supported_stsc_samples_per_chunk(
    moov: bytes, track: TrackSummary, error: str
) -> int:
    stsc_boxes = [box for box in _track_boxes(moov, track.track_id) if box.type == "stsc"]
    if len(stsc_boxes) != 1:
        raise ValueError(error)
    stsc = stsc_boxes[0]
    if u32(moov, stsc.body_offset + 4) != 1:
        raise ValueError(error)
    first_chunk = u32(moov, stsc.body_offset + 8)
    samples_per_chunk = u32(moov, stsc.body_offset + 12)
    sample_description_index = u32(moov, stsc.body_offset + 16)
    if first_chunk != 1 or not samples_per_chunk or sample_description_index != 1:
        raise ValueError(error)
    return samples_per_chunk


def _validate_service_patches(
    layout: BrawLayout,
    video_track: TrackSummary,
    frames: list[HiddenFrame],
    service_patches: dict[int, ServicePatch],
    service_gaps: list[ServiceGap] | None,
) -> None:
    if service_patches and not service_gaps:
        raise ValueError("service patch requires service gap evidence")
    if set(service_patches) != {patch.track_id for patch in service_patches.values()}:
        raise ValueError("service patch keys must match track IDs")

    indexed_ranges = [
        sample_range
        for candidate in layout.tracks.values()
        for sample_range in _indexed_track_ranges(
            layout.moov,
            candidate,
            "video track" if candidate.track_id == video_track.track_id else "non-video track",
        )
    ]
    accepted_ranges: list[tuple[int, int]] = []
    with layout.path.open("rb") as source:
        for track_id, patch in service_patches.items():
            if track_id == video_track.track_id:
                raise ValueError("service patch cannot target the video track")
            track = layout.tracks.get(track_id)
            if track is None:
                raise ValueError("service patch track is missing from source")
            _validate_service_track_structure(layout.moov, track)
            if patch.added_samples <= 0 or len(patch.offsets) != 1:
                raise ValueError("service patch must provide one offset and positive sample count")
            fixed_size = _fixed_stsz_size_for_track(layout.moov, track)
            _track_media_duration(track, len(track.sizes), "service track")
            samples_per_chunk = _supported_stsc_samples_per_chunk(
                layout.moov,
                track,
                "service track stsc mapping is unsupported for MVP repair",
            )
            if len(track.sizes) != len(track.offsets) * samples_per_chunk:
                raise ValueError("service track stsc mapping does not match indexed samples")
            if patch.added_samples != samples_per_chunk:
                raise ValueError("service patch sample count must match the supported stsc chunk size")

            offset = patch.offsets[0]
            end = offset + fixed_size * patch.added_samples
            if not 0 <= offset < layout.moov_offset or end > layout.moov_offset:
                raise ValueError("service patch extends outside mdat")
            if service_gaps is not None and not contains_service_range(service_gaps, offset, end):
                raise ValueError("service patch range is outside supplied service gaps")
            if any(offset < accepted_end and accepted_start < end for accepted_start, accepted_end in accepted_ranges):
                raise ValueError("service patch overlaps another service patch")
            if any(
                offset < sample_start + sample_size and sample_start < end
                for sample_start, sample_size in indexed_ranges
            ):
                raise ValueError("service patch overlaps indexed track sample")
            if any(offset < frame.offset + frame.size and frame.offset < end for frame in frames):
                raise ValueError("service patch overlaps hidden video frame")
            source.seek(offset)
            if len(source.read(end - offset)) != end - offset:
                raise ValueError("source ended before service patch data")
            accepted_ranges.append((offset, end))


def _rebuild_box(raw: bytes, patches: _CandidatePatches, track_id: int | None = None) -> bytes:
    box_type = raw[4:8].decode("latin-1", "replace")
    header_size = _header_size(raw)
    body_start = header_size + (4 if box_type == "meta" else 0)
    current_track_id = _track_id(raw) if box_type == "trak" else track_id
    patch = (
        patches.video
        if current_track_id == patches.video.track_id
        else patches.service_tracks.get(current_track_id)
    )

    if box_type == "mvhd" and patches.movie_duration is not None:
        return _patch_duration(raw, box_type, patches.movie_duration)
    if patch and box_type == "tkhd":
        return _patch_duration(raw, box_type, patch.movie_duration)
    if patch and box_type == "mdhd":
        return _patch_duration(raw, box_type, patch.media_duration)
    if patch and box_type == "elst":
        return _patch_elst(raw, patch.movie_duration)
    if patch and box_type == "stts":
        return _patch_stts(raw, patch.sample_count)
    if patch and box_type == "stsz":
        return _patch_stsz(raw, patch.sizes)
    if patch and box_type == "co64":
        return _patch_co64(raw, patch.offsets)

    if box_type == "meta":
        return raw
    if box_type in CONTAINERS and body_start < len(raw):
        body = bytearray(raw[header_size:body_start])
        for child in iter_boxes(raw, body_start, len(raw)):
            body.extend(_rebuild_box(raw[child.offset:child.end_offset], patches, current_track_id))
        return _replace_body(raw, bytes(body))
    return raw


def _moov_children(moov: bytes) -> list[Box]:
    moov_boxes = list(iter_boxes(moov, 0, len(moov)))
    if len(moov_boxes) != 1 or moov_boxes[0].type != "moov":
        raise ValueError("moov must contain exactly one movie box")
    movie = moov_boxes[0]
    return list(iter_boxes(moov, movie.body_offset, movie.end_offset))


def _walk_repair_boxes(data: bytes, start: int, end: int, path: str = ""):
    for box in iter_boxes(data, start, end):
        cur_path = f"{path}/{box.type}" if path else box.type
        current = Box(box.offset, box.size, box.header_size, box.type, cur_path)
        yield current
        child_start = box.body_offset + (4 if box.type == "meta" else 0)
        if box.type in CONTAINERS and box.type != "meta" and child_start < box.end_offset:
            yield from _walk_repair_boxes(data, child_start, box.end_offset, cur_path)


def _track_id(raw: bytes) -> int | None:
    for box in iter_boxes(raw, _header_size(raw), len(raw)):
        if box.type != "tkhd":
            continue
        version = raw[box.body_offset]
        return u32(raw, box.body_offset + (20 if version else 12))
    return None


def _patch_duration(raw: bytes, box_type: str, duration: int) -> bytes:
    updated = bytearray(raw)
    header_size = _header_size(raw)
    version = updated[header_size]
    offset = {
        "mvhd": 24 if version else 16,
        "tkhd": 28 if version else 20,
        "mdhd": 24 if version else 16,
    }[box_type] + header_size
    width = 8 if version else 4
    updated[offset:offset + width] = p64(duration) if version else p32(duration)
    return bytes(updated)


def _patch_elst(raw: bytes, duration: int) -> bytes:
    _validate_elst(raw, "track")
    updated = bytearray(raw)
    header_size = _header_size(raw)
    version = updated[header_size]
    offset = header_size + 8
    width = 8 if version else 4
    updated[offset:offset + width] = p64(duration) if version else p32(duration)
    return bytes(updated)


def _validate_elst(raw: bytes, track_kind: str) -> None:
    header_size = _header_size(raw)
    version = raw[header_size]
    if version not in {0, 1}:
        raise ValueError(f"{track_kind} elst version is unsupported for MVP repair")
    if u32(raw, header_size + 4) != 1:
        raise ValueError(f"{track_kind} elst must have one entry for MVP repair")

    entry_offset = header_size + 8
    media_time_offset = entry_offset + (8 if version else 4)
    media_time_width = 8 if version else 4
    if any(raw[media_time_offset:media_time_offset + media_time_width]):
        raise ValueError(f"{track_kind} elst media_time must be zero for MVP repair")
    rate_offset = media_time_offset + media_time_width
    if raw[rate_offset:rate_offset + 2] != b"\0\1" or raw[rate_offset + 2:rate_offset + 4] != b"\0\0":
        raise ValueError(f"{track_kind} elst rate must be 1.0 for MVP repair")


def _patch_stts(raw: bytes, sample_count: int) -> bytes:
    header_size = _header_size(raw)
    if u32(raw, header_size + 4) != 1:
        raise ValueError("video track stts must have one entry for MVP repair")
    updated = bytearray(raw)
    updated[header_size + 8:header_size + 12] = p32(sample_count)
    return bytes(updated)


def _patch_stsz(raw: bytes, sizes: list[int]) -> bytes:
    header_size = _header_size(raw)
    fixed_size = u32(raw, header_size + 4)
    if fixed_size:
        if any(size != fixed_size for size in sizes):
            raise ValueError("fixed-size stsz cannot represent hidden frame sizes")
        updated = bytearray(raw)
        updated[header_size + 8:header_size + 12] = p32(len(sizes))
        return bytes(updated)
    body = bytearray(raw[header_size:header_size + 12])
    body[8:12] = p32(len(sizes))
    for size in sizes:
        body.extend(p32(size))
    return _replace_body(raw, bytes(body))


def _patch_co64(raw: bytes, offsets: list[int]) -> bytes:
    header_size = _header_size(raw)
    body = bytearray(raw[header_size:header_size + 8])
    body[4:8] = p32(len(offsets))
    for offset in offsets:
        body.extend(p64(offset))
    return _replace_body(raw, bytes(body))


def _header_size(raw: bytes) -> int:
    return 16 if u32(raw, 0) == 1 else 8


def _replace_body(raw: bytes, body: bytes) -> bytes:
    box_type = raw[4:8]
    size = 8 + len(body)
    if _header_size(raw) == 16:
        return p32(1) + box_type + p64(16 + len(body)) + body
    if size > 0xFFFFFFFF:
        return p32(1) + box_type + p64(16 + len(body)) + body
    return p32(size) + box_type + body


def _copy_candidate(layout: BrawLayout, source: Path, output: Path, moov: bytes) -> None:
    if output.exists():
        raise FileExistsError(output)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent, prefix=f".{output.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as writer, source.open("rb") as reader:
            _copy_exact(reader, writer, layout.mdat_size)
            writer.write(moov)
            reader.seek(layout.moov_offset + layout.moov_size)
            while chunk := reader.read(64 * 1024 * 1024):
                writer.write(chunk)
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_exact(reader, writer, size: int) -> None:
    remaining = size
    while remaining:
        chunk = reader.read(min(64 * 1024 * 1024, remaining))
        if not chunk:
            raise IOError("source ended before mdat copy completed")
        writer.write(chunk)
        remaining -= len(chunk)
