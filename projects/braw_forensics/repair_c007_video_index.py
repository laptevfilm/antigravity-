#!/usr/bin/env python3
import json
import shutil
import struct
import sys
from pathlib import Path


def u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def u64(b, o):
    return struct.unpack_from(">Q", b, o)[0]


def p32(n):
    return struct.pack(">I", n)


def p64(n):
    return struct.pack(">Q", n)


CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "tref", "dinf", "udta", "meta"}
REBUILD_CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl"}
FRAME_PATTERN = b"\x00\x00\x01\x00bmdf\x00\x00\x00\x10srte"


def iter_boxes(buf, start, end):
    p = start
    while p + 8 <= end:
        size = u32(buf, p)
        typ = buf[p + 4:p + 8].decode("latin-1")
        hdr = 8
        if size == 1:
            size = u64(buf, p + 8)
            hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr or p + size > end:
            raise ValueError(f"invalid box {typ!r} at {p}, size {size}")
        yield p, size, hdr, typ
        p += size
    if p != end:
        raise ValueError(f"box parse stopped at {p}, expected {end}")


def read_mdat_and_moov(src):
    with src.open("rb") as f:
        head = f.read(16)
        if head[4:8] != b"mdat":
            raise ValueError("expected mdat-first BRAW")
        mdat_size = u64(head, 8) if u32(head, 0) == 1 else u32(head, 0)
        f.seek(mdat_size)
        moov_head = f.read(8)
        if moov_head[4:8] != b"moov":
            raise ValueError(f"moov not found at mdat end {mdat_size}")
        moov_size = u32(moov_head, 0)
        f.seek(mdat_size)
        moov = f.read(moov_size)
    return mdat_size, moov


def find_video_tables(moov):
    for trak_off, trak_size, trak_hdr, typ in iter_boxes(moov, 8, len(moov)):
        if typ != "trak":
            continue
        trak = moov[trak_off:trak_off + trak_size]
        track_id = None
        stsz = None
        co64 = None
        for off, size, hdr, child_typ in walk_boxes(trak, 8, len(trak)):
            body = off + hdr
            if child_typ == "tkhd":
                track_id = u32(trak, body + 12)
            elif child_typ == "stsz":
                n = u32(trak, body + 8)
                sizes = [u32(trak, body + 12 + i * 4) for i in range(n)]
                stsz = sizes
            elif child_typ == "co64":
                n = u32(trak, body + 4)
                co64 = [u64(trak, body + 8 + i * 8) for i in range(n)]
        if track_id == 1:
            if not stsz or not co64 or len(stsz) != len(co64):
                raise ValueError("video track tables are incomplete")
            return stsz, co64
    raise ValueError("video track not found")


def walk_boxes(buf, start, end):
    for off, size, hdr, typ in iter_boxes(buf, start, end):
        yield off, size, hdr, typ
        child_start = off + hdr + (4 if typ == "meta" else 0)
        if typ in CONTAINERS and child_start < off + size:
            yield from walk_boxes(buf, child_start, off + size)


def scan_hidden_frames(src, start, moov_offset):
    hits = []
    overlap = len(FRAME_PATTERN) - 1
    prev = b""
    chunk = 64 * 1024 * 1024
    with src.open("rb") as f:
        f.seek(start)
        base = start
        while base < moov_offset:
            n = min(chunk, moov_offset - base)
            buf = prev + f.read(n)
            if len(buf) <= len(prev):
                break
            search_from = 0
            while True:
                j = buf.find(FRAME_PATTERN, search_from)
                if j < 0:
                    break
                hits.append(base - len(prev) + j)
                search_from = j + 1
            base += n
            prev = buf[-overlap:]

    sizes = []
    with src.open("rb") as f:
        for i, off in enumerate(hits):
            f.seek(off)
            head = f.read(272)
            if head[:len(FRAME_PATTERN)] != FRAME_PATTERN:
                raise ValueError(f"bad frame pattern at {off}")
            if head[256:260] != b"braw":
                raise ValueError(f"missing braw payload marker at {off + 256}")
            payload = u32(head, 260)
            size = payload + 256
            next_limit = hits[i + 1] if i + 1 < len(hits) else moov_offset
            if off + size > next_limit:
                raise ValueError(f"frame at {off} overlaps next data")
            sizes.append(size)
    return hits, sizes


def patch_duration_box(raw, typ, new_duration):
    b = bytearray(raw)
    hdr = 16 if u32(b, 0) == 1 else 8
    version = b[hdr]
    body = hdr
    if typ == "mvhd":
        dur_off = body + (24 if version == 1 else 16)
    elif typ == "tkhd":
        dur_off = body + (32 if version == 1 else 20)
    elif typ == "mdhd":
        dur_off = body + (28 if version == 1 else 16)
    else:
        return raw
    if version == 1:
        b[dur_off:dur_off + 8] = p64(new_duration)
    else:
        b[dur_off:dur_off + 4] = p32(new_duration)
    return bytes(b)


def trak_id(raw):
    for off, size, hdr, typ in walk_boxes(raw, 8, len(raw)):
        if typ == "tkhd":
            return u32(raw, off + hdr + 12)
    return None


def rebuild_box(raw, video_count, video_sizes, video_offsets, track_scope=None):
    typ = raw[4:8].decode("latin-1")
    hdr = 16 if u32(raw, 0) == 1 else 8
    body_start = hdr + (4 if typ == "meta" else 0)

    if typ == "mvhd":
        return patch_duration_box(raw, typ, video_count)

    this_trak_id = trak_id(raw) if typ == "trak" else None
    active_track = this_trak_id if this_trak_id is not None else track_scope
    patch_video_track = active_track == 1
    patch_clip_track = active_track == 2

    if typ in REBUILD_CONTAINERS and body_start < len(raw):
        prefix = raw[hdr:body_start]
        body = bytearray(prefix)
        for off, size, child_hdr, child_typ in iter_boxes(raw, body_start, len(raw)):
            child = raw[off:off + size]
            if patch_video_track and child_typ in {"tkhd", "mdhd"}:
                child = patch_duration_box(child, child_typ, video_count)
            elif patch_clip_track and child_typ in {"tkhd", "mdhd"}:
                child = patch_duration_box(child, child_typ, video_count)
            else:
                child = rebuild_box(child, video_count, video_sizes, video_offsets, active_track)
            body.extend(child)
        return p32(8 + len(body)) + raw[4:8] + bytes(body)

    if patch_video_track and typ == "stts":
        b = bytearray(raw)
        b[16:20] = p32(video_count)
        return bytes(b)

    if patch_clip_track and typ == "stts":
        b = bytearray(raw)
        b[20:24] = p32(video_count)
        return bytes(b)

    if patch_video_track and typ == "stsz":
        body = bytearray(raw[8:20])
        body[8:12] = p32(video_count)
        for size in video_sizes:
            body.extend(p32(size))
        return p32(8 + len(body)) + b"stsz" + bytes(body)

    if patch_video_track and typ == "co64":
        body = bytearray(raw[8:16])
        body[4:8] = p32(video_count)
        for off in video_offsets:
            body.extend(p64(off))
        return p32(8 + len(body)) + b"co64" + bytes(body)

    return raw


def copy_prefix_and_moov(src, dst, mdat_size, new_moov):
    if dst.exists():
        raise FileExistsError(dst)
    with src.open("rb") as r, dst.open("wb") as w:
        remaining = mdat_size
        while remaining:
            chunk = r.read(min(64 * 1024 * 1024, remaining))
            if not chunk:
                raise IOError("source ended before mdat copy completed")
            w.write(chunk)
            remaining -= len(chunk)
        w.write(new_moov)


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    report = Path(sys.argv[3])

    mdat_size, moov = read_mdat_and_moov(src)
    old_sizes, old_offsets = find_video_tables(moov)
    last_video_end = old_offsets[-1] + old_sizes[-1]
    hidden_offsets, hidden_sizes = scan_hidden_frames(src, last_video_end, mdat_size)
    if len(hidden_offsets) != 125:
        raise ValueError(f"expected 125 hidden frames, found {len(hidden_offsets)}")

    all_sizes = old_sizes + hidden_sizes
    all_offsets = old_offsets + hidden_offsets
    new_moov = rebuild_box(moov, len(all_sizes), all_sizes, all_offsets)
    copy_prefix_and_moov(src, dst, mdat_size, new_moov)

    result = {
        "source": str(src),
        "candidate": str(dst),
        "original_video_frames": len(old_sizes),
        "hidden_video_frames_added": len(hidden_sizes),
        "new_video_frames": len(all_sizes),
        "original_duration_seconds_at_25fps": len(old_sizes) / 25,
        "added_duration_seconds_at_25fps": len(hidden_sizes) / 25,
        "new_duration_seconds_at_25fps": len(all_sizes) / 25,
        "first_hidden_offset": hidden_offsets[0],
        "last_hidden_offset": hidden_offsets[-1],
        "last_hidden_size": hidden_sizes[-1],
        "last_hidden_end": hidden_offsets[-1] + hidden_sizes[-1],
        "mdat_end_moov_offset": mdat_size,
        "old_moov_size": len(moov),
        "new_moov_size": len(new_moov),
        "candidate_size": dst.stat().st_size,
        "size_delta_vs_source": dst.stat().st_size - src.stat().st_size,
        "hidden_size_min": min(hidden_sizes),
        "hidden_size_max": max(hidden_sizes),
        "hidden_size_first10": hidden_sizes[:10],
        "hidden_size_last10": hidden_sizes[-10:],
    }
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()




