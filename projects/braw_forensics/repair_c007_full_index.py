#!/usr/bin/env python3
import json
import struct
import sys
from pathlib import Path


def u32(b, o): return struct.unpack_from('>I', b, o)[0]
def u64(b, o): return struct.unpack_from('>Q', b, o)[0]
def p32(n): return struct.pack('>I', n)
def p64(n): return struct.pack('>Q', n)

CONTAINERS = {'moov', 'trak', 'mdia', 'minf', 'stbl', 'edts', 'tref', 'dinf', 'udta', 'meta'}
REBUILD_CONTAINERS = {'moov', 'trak', 'edts', 'mdia', 'minf', 'stbl'}
FRAME_PATTERN = b'\x00\x00\x01\x00bmdf\x00\x00\x00\x10srte'


def iter_boxes(buf, start, end):
    p = start
    while p + 8 <= end:
        size = u32(buf, p)
        typ = buf[p + 4:p + 8].decode('latin-1')
        hdr = 8
        if size == 1:
            size = u64(buf, p + 8)
            hdr = 16
        elif size == 0:
            size = end - p
        if size < hdr or p + size > end:
            raise ValueError(f'invalid box {typ!r} at {p}, size {size}')
        yield p, size, hdr, typ
        p += size
    if p != end:
        raise ValueError(f'box parse stopped at {p}, expected {end}')


def walk_boxes(buf, start, end):
    for off, size, hdr, typ in iter_boxes(buf, start, end):
        yield off, size, hdr, typ
        child_start = off + hdr + (4 if typ == 'meta' else 0)
        if typ in CONTAINERS and child_start < off + size:
            yield from walk_boxes(buf, child_start, off + size)


def read_mdat_and_moov(src):
    with src.open('rb') as f:
        head = f.read(16)
        if head[4:8] != b'mdat':
            raise ValueError('expected mdat-first BRAW')
        mdat_size = u64(head, 8) if u32(head, 0) == 1 else u32(head, 0)
        f.seek(mdat_size)
        moov_head = f.read(8)
        if moov_head[4:8] != b'moov':
            raise ValueError('moov not found at mdat end')
        moov_size = u32(moov_head, 0)
        f.seek(mdat_size)
        return mdat_size, f.read(moov_size)


def trak_id(raw):
    for off, size, hdr, typ in walk_boxes(raw, 8, len(raw)):
        if typ == 'tkhd':
            return u32(raw, off + hdr + 12)
    return None


def find_track_tables(moov):
    tracks = {}
    for trak_off, trak_size, trak_hdr, typ in iter_boxes(moov, 8, len(moov)):
        if typ != 'trak':
            continue
        trak = moov[trak_off:trak_off + trak_size]
        info = {}
        for off, size, hdr, child_typ in walk_boxes(trak, 8, len(trak)):
            body = off + hdr
            if child_typ == 'tkhd':
                info['id'] = u32(trak, body + 12)
            elif child_typ == 'stsz':
                sample_size = u32(trak, body + 4)
                count = u32(trak, body + 8)
                sizes = [sample_size] * count if sample_size else [u32(trak, body + 12 + i * 4) for i in range(count)]
                info['sample_size'] = sample_size
                info['sizes'] = sizes
            elif child_typ == 'co64':
                count = u32(trak, body + 4)
                info['offsets'] = [u64(trak, body + 8 + i * 8) for i in range(count)]
        if 'id' in info:
            tracks[info['id']] = info
    return tracks


def scan_hidden_video(src, start, moov_offset):
    hits = []
    overlap = len(FRAME_PATTERN) - 1
    prev = b''
    chunk = 64 * 1024 * 1024
    with src.open('rb') as f:
        f.seek(start)
        base = start
        while base < moov_offset:
            n = min(chunk, moov_offset - base)
            buf = prev + f.read(n)
            if len(buf) <= len(prev):
                break
            pos = 0
            while True:
                j = buf.find(FRAME_PATTERN, pos)
                if j < 0:
                    break
                hits.append(base - len(prev) + j)
                pos = j + 1
            base += n
            prev = buf[-overlap:]
    sizes = []
    with src.open('rb') as f:
        for i, off in enumerate(hits):
            f.seek(off + 256)
            marker = f.read(8)
            if marker[:4] != b'braw':
                raise ValueError(f'missing braw marker at {off + 256}')
            size = u32(marker, 4) + 256
            next_limit = hits[i + 1] if i + 1 < len(hits) else moov_offset
            if off + size > next_limit:
                raise ValueError(f'hidden frame overlaps next data at {off}')
            sizes.append(size)
    return hits, sizes


def floor_align(n, align=256):
    return n - (n % align)


def first_nonzero_offset(src, start, end):
    with src.open('rb') as f:
        f.seek(start)
        base = start
        while base < end:
            data = f.read(min(1024 * 1024, end - base))
            if not data:
                break
            for i, value in enumerate(data):
                if value:
                    return base + i
            base += len(data)
    return None


def infer_hidden_service_offsets(src, hidden_offsets, hidden_sizes, moov_offset):
    medium = []
    large = []
    for i, off in enumerate(hidden_offsets):
        next_off = hidden_offsets[i + 1] if i + 1 < len(hidden_offsets) else moov_offset
        gap_start = off + hidden_sizes[i]
        gap = next_off - gap_start
        if 30_000 < gap < 80_000:
            nz = first_nonzero_offset(src, gap_start, next_off)
            medium.append(floor_align(nz))
        elif 250_000 < gap < 400_000:
            nz = first_nonzero_offset(src, gap_start, next_off)
            large.append(floor_align(nz))
    if len(medium) != 5 or len(large) != 5:
        raise ValueError(f'expected 5 medium and 5 large service gaps, found {len(medium)} and {len(large)}')
    return {
        3: large,
        4: medium,
        5: [off + 20480 for off in medium],
    }


def patch_duration_box(raw, typ, new_duration):
    b = bytearray(raw)
    hdr = 16 if u32(b, 0) == 1 else 8
    version = b[hdr]
    body = hdr
    if typ == 'mvhd':
        dur_off = body + (24 if version == 1 else 16)
    elif typ == 'tkhd':
        dur_off = body + (32 if version == 1 else 20)
    elif typ == 'mdhd':
        dur_off = body + (28 if version == 1 else 16)
    else:
        return raw
    if version == 1:
        b[dur_off:dur_off + 8] = p64(new_duration)
    else:
        b[dur_off:dur_off + 4] = p32(new_duration)
    return bytes(b)


def patch_elst_box(raw, new_duration):
    b = bytearray(raw)
    hdr = 16 if u32(b, 0) == 1 else 8
    version = b[hdr]
    entries = u32(b, hdr + 4)
    if entries >= 1:
        dur_off = hdr + 8
        if version == 1:
            b[dur_off:dur_off + 8] = p64(new_duration)
        else:
            b[dur_off:dur_off + 4] = p32(new_duration)
    return bytes(b)


def rebuild_box(raw, patches, track_scope=None):
    typ = raw[4:8].decode('latin-1')
    hdr = 16 if u32(raw, 0) == 1 else 8
    body_start = hdr + (4 if typ == 'meta' else 0)

    if typ == 'mvhd':
        return patch_duration_box(raw, typ, patches['mvhd_duration'])

    this_id = trak_id(raw) if typ == 'trak' else None
    active_track = this_id if this_id is not None else track_scope
    track_patch = patches['tracks'].get(active_track)

    if track_patch and typ == 'elst':
        return patch_elst_box(raw, track_patch['tkhd_duration'])

    if typ in REBUILD_CONTAINERS and body_start < len(raw):
        body = bytearray(raw[hdr:body_start])
        for off, size, child_hdr, child_typ in iter_boxes(raw, body_start, len(raw)):
            child = raw[off:off + size]
            if track_patch and child_typ in {'tkhd', 'mdhd'}:
                duration_key = 'tkhd_duration' if child_typ == 'tkhd' else 'mdhd_duration'
                child = patch_duration_box(child, child_typ, track_patch[duration_key])
            else:
                child = rebuild_box(child, patches, active_track)
            body.extend(child)
        return p32(8 + len(body)) + raw[4:8] + bytes(body)

    if track_patch and typ == 'stts':
        b = bytearray(raw)
        entries = u32(b, 12)
        if entries == 1:
            b[16:20] = p32(track_patch['stts_sample_count'])
            if 'stts_delta' in track_patch:
                b[20:24] = p32(track_patch['stts_delta'])
        return bytes(b)

    if track_patch and typ == 'stsz':
        sample_size = u32(raw, 12)
        if sample_size == 0:
            body = bytearray(raw[8:20])
            body[8:12] = p32(len(track_patch['sizes']))
            for size in track_patch['sizes']:
                body.extend(p32(size))
            return p32(8 + len(body)) + b'stsz' + bytes(body)
        b = bytearray(raw)
        b[16:20] = p32(track_patch['stsz_count'])
        return bytes(b)

    if track_patch and typ == 'co64':
        body = bytearray(raw[8:16])
        offsets = track_patch['offsets']
        body[4:8] = p32(len(offsets))
        for off in offsets:
            body.extend(p64(off))
        return p32(8 + len(body)) + b'co64' + bytes(body)

    return raw


def copy_prefix_and_moov(src, dst, mdat_size, old_moov_size, new_moov):
    if dst.exists():
        raise FileExistsError(dst)
    with src.open('rb') as r, dst.open('wb') as w:
        remaining = mdat_size
        while remaining:
            chunk = r.read(min(64 * 1024 * 1024, remaining))
            if not chunk:
                raise IOError('source ended before mdat copy completed')
            w.write(chunk)
            remaining -= len(chunk)
        w.write(new_moov)
        r.seek(mdat_size + old_moov_size)
        trailing = r.read()
        if trailing:
            w.write(trailing)


def main():
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    report = Path(sys.argv[3])
    mdat_size, moov = read_mdat_and_moov(src)
    tracks = find_track_tables(moov)
    old_video_sizes = tracks[1]['sizes']
    old_video_offsets = tracks[1]['offsets']
    last_video_end = old_video_offsets[-1] + old_video_sizes[-1]
    hidden_offsets, hidden_sizes = scan_hidden_video(src, last_video_end, mdat_size)
    service = infer_hidden_service_offsets(src, hidden_offsets, hidden_sizes, mdat_size)

    video_sizes = old_video_sizes + hidden_sizes
    video_offsets = old_video_offsets + hidden_offsets
    audio_offsets = tracks[3]['offsets'] + service[3]
    meta4_offsets = tracks[4]['offsets'] + service[4]
    meta5_offsets = tracks[5]['offsets'] + service[5]

    patches = {
        'mvhd_duration': 881,
        'tracks': {
            1: {'tkhd_duration': 881, 'mdhd_duration': 881, 'stts_sample_count': 881, 'stsz_count': 881, 'sizes': video_sizes, 'offsets': video_offsets},
            2: {'tkhd_duration': 881, 'mdhd_duration': 881, 'stts_sample_count': 1, 'stts_delta': 881, 'stsz_count': 1, 'sizes': tracks[2]['sizes'], 'offsets': tracks[2]['offsets']},
            3: {'tkhd_duration': 875, 'mdhd_duration': 1680000, 'stts_sample_count': 1680000, 'stsz_count': 1680000, 'sizes': tracks[3]['sizes'], 'offsets': audio_offsets},
            4: {'tkhd_duration': 870, 'mdhd_duration': 38912, 'stts_sample_count': 38912, 'stsz_count': 38912, 'sizes': tracks[4]['sizes'], 'offsets': meta4_offsets},
            5: {'tkhd_duration': 870, 'mdhd_duration': 38912, 'stts_sample_count': 38912, 'stsz_count': 38912, 'sizes': tracks[5]['sizes'], 'offsets': meta5_offsets},
        }
    }
    new_moov = rebuild_box(moov, patches)
    copy_prefix_and_moov(src, dst, mdat_size, len(moov), new_moov)
    result = {
        'source': str(src),
        'candidate': str(dst),
        'video_frames': {'old': len(old_video_sizes), 'added': len(hidden_sizes), 'new': len(video_sizes)},
        'duration_target_seconds': 35.24,
        'audio_chunks': {'old': len(tracks[3]['offsets']), 'added_offsets': service[3], 'new': len(audio_offsets)},
        'metadata_track4_chunks': {'old': len(tracks[4]['offsets']), 'added_offsets': service[4], 'new': len(meta4_offsets)},
        'metadata_track5_chunks': {'old': len(tracks[5]['offsets']), 'added_offsets': service[5], 'new': len(meta5_offsets)},
        'old_moov_size': len(moov),
        'new_moov_size': len(new_moov),
        'candidate_size': dst.stat().st_size,
    }
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()


