from pathlib import Path

import pytest

from brawrec.bmff.boxes import u32, walk_boxes
from brawrec.braw.tables import parse_braw_layout
from brawrec.recovery.repair import ServicePatch, build_repair_plan, write_candidate
from brawrec.recovery.scan import FRAME_PATTERN, HiddenFrame
from brawrec.recovery.service_gaps import ServiceGap
from tests.fixtures import synthetic_braw, trak


def test_service_patch_records_offsets_and_samples():
    patch = ServicePatch(track_id=5, offsets=[13_303_263_232], added_samples=48_000)

    assert patch.track_id == 5
    assert patch.offsets == [13_303_263_232]
    assert patch.added_samples == 48_000


def test_write_candidate_extends_fixed_size_service_track_from_explicit_patch(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            500_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(
                    5,
                    b"sowt",
                    [4] * 48_000,
                    [2_048],
                    timescale=48_000,
                    fixed_size=4,
                    tkhd_duration=48_000,
                    elst_entries=1,
                    stsc_entries=[(1, 48_000, 1)],
                )
            ],
        )
    )
    payload[2_048 : 2_048 + 4 * 48_000] = b"\x01" * (4 * 48_000)
    payload[200_000 : 200_000 + 4 * 48_000] = b"\x02" * (4 * 48_000)
    source.write_bytes(payload)
    layout = parse_braw_layout(source)
    hidden = HiddenFrame(offset=512, size=556)
    payload = bytearray(source.read_bytes())
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)
    output = tmp_path / "candidate.braw"
    patch = ServicePatch(track_id=5, offsets=[200_000], added_samples=48_000)
    gap = ServiceGap("large", 1_068, layout.moov_offset, 2_048, 2_048)

    plan = build_repair_plan(
        parse_braw_layout(source), output, [hidden], service_patches={5: patch}, service_gaps=[gap]
    )
    write_candidate(plan)

    candidate = parse_braw_layout(output)
    service_track = candidate.tracks[5]
    assert service_track.offsets == [2_048, 200_000]
    assert len(service_track.sizes) == 96_000
    assert service_track.stts == [(96_000, 1)]
    assert service_track.mdhd_duration == 96_000
    assert service_track.tkhd_duration == 50
    service_elst = next(
        box for box in walk_boxes(candidate.moov, 0, len(candidate.moov))
        if box.path == "moov/trak/edts/elst"
    )
    assert u32(candidate.moov, service_elst.body_offset + 8) == 50
    movie_header = next(
        box for box in walk_boxes(candidate.moov, 0, len(candidate.moov)) if box.path == "moov/mvhd"
    )
    assert u32(candidate.moov, movie_header.body_offset + 16) == 50


def test_build_repair_plan_refuses_service_patch_outside_supplied_gap(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(5, b"sowt", [4], [1_500], fixed_size=4, stsc_entries=[(1, 1, 1)])
            ],
        )
    )
    layout = parse_braw_layout(source)
    hidden = HiddenFrame(offset=512, size=556)
    payload = bytearray(source.read_bytes())
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="service gap"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[2_048], added_samples=1)},
            service_gaps=[ServiceGap("small", 1_068, 1_500, 1_024, 1_024)],
        )


def test_build_repair_plan_requires_service_gap_evidence(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(5, b"sowt", [4], [1_500], fixed_size=4, stsc_entries=[(1, 1, 1)])
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="service gap evidence"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[2_048], added_samples=1)},
        )


def test_build_repair_plan_refuses_service_patch_offset_in_mdat_header(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(5, b"sowt", [4], [1_500], fixed_size=4, stsc_entries=[(1, 1, 1)])
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="service gap"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[12], added_samples=1)},
            service_gaps=[ServiceGap("large", 0, 5_000, 16, 0)],
        )


def test_build_repair_plan_refuses_overlapping_service_patches(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(5, b"sowt", [4], [1_500], fixed_size=4, stsc_entries=[(1, 1, 1)]),
                trak(6, b"tmcd", [4], [1_600], fixed_size=4, stsc_entries=[(1, 1, 1)]),
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="another service patch"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={
                5: ServicePatch(track_id=5, offsets=[2_048], added_samples=1),
                6: ServicePatch(track_id=6, offsets=[2_050], added_samples=1),
            },
            service_gaps=[ServiceGap("small", 1_068, 5_000, 1_068, 1_068)],
        )


def test_build_repair_plan_refuses_unsupported_service_stsc(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(
                    5,
                    b"sowt",
                    [4],
                    [1_500],
                    fixed_size=4,
                    stsc_entries=[(1, 1, 1), (2, 1, 1)],
                )
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="stsc"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[2_048], added_samples=1)},
            service_gaps=[ServiceGap("small", 1_068, 5_000, 1_068, 1_068)],
        )


def test_build_repair_plan_refuses_equal_count_non_video_with_unsupported_stsc(
    tmp_path: Path,
):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(
                    5,
                    b"sowt",
                    [4],
                    [1_500],
                    fixed_size=4,
                    stsc_entries=[(1, 1, 1), (2, 1, 1)],
                )
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="non-video track sample mapping"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_refuses_equal_count_non_video_with_inconsistent_stsc(
    tmp_path: Path,
):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(
                    5,
                    b"sowt",
                    [4],
                    [1_500],
                    fixed_size=4,
                    stsc_entries=[(1, 2, 1)],
                )
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="non-video track sample mapping"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_refuses_service_patch_overlapping_existing_chunk(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(
                    5,
                    b"sowt",
                    [4] * 4,
                    [1_500],
                    fixed_size=4,
                    stsc_entries=[(1, 4, 1)],
                )
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="indexed track sample"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[1_508], added_samples=4)},
            service_gaps=[ServiceGap("small", 1_068, 5_000, 1_068, 1_068)],
        )


def test_build_repair_plan_refuses_ambiguous_fixed_size_non_video_track(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[trak(5, b"sowt", [4, 4], [1_500], fixed_size=4)],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="non-video track sample mapping"):
        build_repair_plan(parse_braw_layout(source), tmp_path / "candidate.braw", [hidden])


def test_build_repair_plan_requires_service_gap_to_contain_entire_patch_range(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(
        synthetic_braw(
            [100],
            [256],
            5_000,
            movie_timescale=25,
            movie_duration=1,
            extra_tracks=[
                trak(5, b"sowt", [4], [1_500], fixed_size=4, stsc_entries=[(1, 1, 1)])
            ],
        )
    )
    hidden = HiddenFrame(offset=512, size=556)
    payload[512 : 512 + len(FRAME_PATTERN)] = FRAME_PATTERN
    payload[768:772] = b"braw"
    payload[772:776] = (300).to_bytes(4, "big")
    source.write_bytes(payload)

    with pytest.raises(ValueError, match="service gap"):
        build_repair_plan(
            parse_braw_layout(source),
            tmp_path / "candidate.braw",
            [hidden],
            service_patches={5: ServicePatch(track_id=5, offsets=[2_048], added_samples=1)},
            service_gaps=[ServiceGap("small", 1_068, 2_050, 1_024, 1_024)],
        )
