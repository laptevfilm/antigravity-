#!/usr/bin/env python3
import json
import struct
import sys
from pathlib import Path


def u32(b, o): return struct.unpack_from(">I", b, o)[0]


def load_tables(path):
    return json.load(open(path, encoding="utf-8"))


def main():
    braw = Path(sys.argv[1])
    tables = load_tables(sys.argv[2])
    track1 = tables["tracks"][0]["boxes"]
    stsz = next(x for x in track1 if x["path"].endswith("/stsz"))
    co64 = next(x for x in track1 if x["path"].endswith("/co64"))
    sizes = []
    # The dump stores only first/last sizes; re-read full stsz/co64 from file through moov.
    with open(braw, "rb") as f:
        head = f.read(16)
        mdat_size = struct.unpack_from(">Q", head, 8)[0] if u32(head, 0) == 1 else u32(head, 0)
        f.seek(mdat_size)
        moov = f.read()
    # Use offsets from dump for quick probing.
    offsets = co64["first10"][:-10] if False else None
    # Re-parse specific table locations in moov/trak.
    trak = tables["tracks"][0]
    trak_off = trak["trak_offset_in_moov"]
    stsz_off = trak_off + stsz["offset_in_trak"]
    stsz_body = stsz_off + 8
    count = u32(moov, stsz_body + 8)
    sizes = [u32(moov, stsz_body + 12 + i * 4) for i in range(count)]
    co64_off = trak_off + co64["offset_in_trak"]
    co64_body = co64_off + 8
    off_count = u32(moov, co64_body + 4)
    offsets = [struct.unpack_from(">Q", moov, co64_body + 8 + i * 8)[0] for i in range(off_count)]
    rows = []
    with open(braw, "rb") as f:
        for i in list(range(5)) + list(range(count - 10, count)):
            off = offsets[i]
            size = sizes[i]
            f.seek(off)
            head64 = f.read(64)
            gap = offsets[i+1] - (off + size) if i + 1 < count else None
            rows.append({
                "index": i + 1,
                "offset": off,
                "size": size,
                "gap_to_next_video": gap,
                "head_hex": head64[:32].hex(),
                "head_ascii": ''.join(chr(x) if 32 <= x < 127 else "." for x in head64[:64]),
            })
    last_end = offsets[-1] + sizes[-1]
    with open(braw, "rb") as f:
        f.seek(last_end)
        after = f.read(1024 * 1024)
    pats = {p.decode(): [] for p in [b"braw", b"Blackmagic", b"moov", b"mdat"]}
    for pat in [b"braw", b"Blackmagic", b"moov", b"mdat"]:
        start = 0
        while True:
            pos = after.find(pat, start)
            if pos < 0:
                break
            pats[pat.decode()].append(pos)
            start = pos + 1
    print(json.dumps({
        "sample_count": count,
        "last_video_end": last_end,
        "probe_rows": rows,
        "patterns_in_1m_after_last_video_end": pats,
        "first_256_after_last_video_end_hex": after[:256].hex(),
        "first_256_after_last_video_end_ascii": ''.join(chr(x) if 32 <= x < 127 else "." for x in after[:256]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
