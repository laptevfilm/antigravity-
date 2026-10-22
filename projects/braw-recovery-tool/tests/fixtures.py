from brawrec.bmff.boxes import p32, p64


def box(kind: bytes, body: bytes) -> bytes:
    return p32(8 + len(body)) + kind + body


def fullbox_body(version_flags: bytes = b"\0\0\0\0") -> bytes:
    return version_flags


def tkhd(track_id: int, duration: int, version: int = 0) -> bytes:
    body = bytearray(fullbox_body(bytes([version, 0, 0, 0])))
    body.extend(b"\0" * (16 if version else 8))
    body.extend(p32(track_id))
    body.extend(b"\0" * 4)
    body.extend(p64(duration) if version else p32(duration))
    body.extend(b"\0" * 60)
    return box(b"tkhd", bytes(body))


def mdhd(timescale: int, duration: int, version: int = 0) -> bytes:
    body = bytearray(fullbox_body(bytes([version, 0, 0, 0])))
    body.extend(b"\0" * (16 if version else 8))
    body.extend(p32(timescale))
    body.extend(p64(duration) if version else p32(duration))
    body.extend(b"\0" * 4)
    return box(b"mdhd", bytes(body))


def mvhd(timescale: int, duration: int, version: int = 0) -> bytes:
    body = bytearray(fullbox_body(bytes([version, 0, 0, 0])))
    body.extend(b"\0" * (16 if version else 8))
    body.extend(p32(timescale))
    body.extend(p64(duration) if version else p32(duration))
    return box(b"mvhd", bytes(body))


def stsd(sample_type: bytes) -> bytes:
    body = bytearray(fullbox_body())
    body.extend(p32(1))
    body.extend(p32(16))
    body.extend(sample_type)
    body.extend(b"\0" * 8)
    return box(b"stsd", bytes(body))


def stts(count: int, delta: int) -> bytes:
    return box(b"stts", fullbox_body() + p32(1) + p32(count) + p32(delta))


def stsz(sizes: list[int], fixed_size: int = 0) -> bytes:
    body = bytearray(fullbox_body() + p32(fixed_size) + p32(len(sizes)))
    if not fixed_size:
        for size in sizes:
            body.extend(p32(size))
    return box(b"stsz", bytes(body))


def stsc(entries: list[tuple[int, int, int]]) -> bytes:
    body = bytearray(fullbox_body() + p32(len(entries)))
    for first_chunk, samples_per_chunk, sample_description_index in entries:
        body.extend(p32(first_chunk))
        body.extend(p32(samples_per_chunk))
        body.extend(p32(sample_description_index))
    return box(b"stsc", bytes(body))


def stco(offsets: list[int]) -> bytes:
    body = bytearray(fullbox_body() + p32(len(offsets)))
    for offset in offsets:
        body.extend(p32(offset))
    return box(b"stco", bytes(body))


def elst(
    entries: int,
    duration: int,
    *,
    version: int = 0,
    media_time: int = 0,
    media_rate_integer: int = 1,
    media_rate_fraction: int = 0,
) -> bytes:
    body = bytearray(fullbox_body(bytes([version, 0, 0, 0])) + p32(entries))
    for _ in range(entries):
        body.extend(p64(duration) if version else p32(duration))
        body.extend(
            (media_time & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big")
            if version
            else (media_time & 0xFFFFFFFF).to_bytes(4, "big")
        )
        body.extend(media_rate_integer.to_bytes(2, "big", signed=True))
        body.extend(media_rate_fraction.to_bytes(2, "big", signed=True))
    return box(b"elst", bytes(body))


def co64(offsets: list[int]) -> bytes:
    body = bytearray(fullbox_body() + p32(len(offsets)))
    for offset in offsets:
        body.extend(p64(offset))
    return box(b"co64", bytes(body))


def trak(
    track_id: int,
    sample_type: bytes,
    sizes: list[int],
    offsets: list[int],
    timescale: int = 25,
    tkhd_duration: int | None = None,
    fixed_size: int = 0,
    version: int = 0,
    elst_entries: int | None = None,
    elst_media_time: int = 0,
    elst_rate_integer: int = 1,
    elst_rate_fraction: int = 0,
    offset_table: str = "co64",
    stts_count: int | None = None,
    stsc_entries: list[tuple[int, int, int]] | None = None,
) -> bytes:
    sample_count = len(sizes)
    offsets_box = co64(offsets) if offset_table == "co64" else stco(offsets)
    stbl = box(
        b"stbl",
        stsd(sample_type)
        + stts(sample_count if stts_count is None else stts_count, 1)
        + stsz(sizes, fixed_size)
        + (stsc(stsc_entries) if stsc_entries is not None else b"")
        + offsets_box,
    )
    minf = box(b"minf", stbl)
    mdia = box(b"mdia", mdhd(timescale, sample_count, version) + minf)
    edts = (
        box(
            b"edts",
            elst(
                elst_entries,
                sample_count,
                version=version,
                media_time=elst_media_time,
                media_rate_integer=elst_rate_integer,
                media_rate_fraction=elst_rate_fraction,
            ),
        )
        if elst_entries is not None
        else b""
    )
    return box(
        b"trak",
        tkhd(track_id, sample_count if tkhd_duration is None else tkhd_duration, version) + edts + mdia,
    )


def synthetic_braw(
    sizes: list[int],
    offsets: list[int],
    mdat_size: int,
    sample_type: bytes = b"braw",
    movie_timescale: int | None = None,
    movie_duration: int = 0,
    movie_version: int = 0,
    extra_tracks: list[bytes] | None = None,
    **track_options: object,
) -> bytes:
    movie_header = (
        mvhd(movie_timescale, movie_duration, movie_version) if movie_timescale is not None else b""
    )
    moov = box(
        b"moov",
        movie_header + trak(1, sample_type, sizes, offsets, **track_options) + b"".join(extra_tracks or []),
    )
    return p32(1) + b"mdat" + p64(mdat_size) + b"\0" * (mdat_size - 16) + moov + b"tail"
