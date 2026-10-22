#!/usr/bin/env python3
import json
import sys


def read_extents(f, extents, rel, size):
    out = bytearray()
    pos = rel
    remaining = size
    for ex in extents:
        ex_len = ex["byte_count"]
        if pos >= ex_len:
            pos -= ex_len
            continue
        take = min(remaining, ex_len - pos)
        f.seek(ex["image_offset"] + pos)
        out.extend(f.read(take))
        remaining -= take
        pos = 0
        if remaining == 0:
            break
    return bytes(out)


inv = json.load(open(sys.argv[1], encoding="utf-8"))
tracks = json.load(open(sys.argv[2], encoding="utf-8"))
path = sys.argv[3]
b = next(x for x in inv["braws"] if x["path"] == path)
tr = next(x for x in tracks if x["path"] == path)
video = tr["tracks"][0]
moov = next(x for x in b["top_boxes"] if x["type"] == "moov")
visible_end = 8 + video["stsz_sample_bytes_total"]
gap_end = moov["offset"]
chunk = 8 * 1024 * 1024
last = None

with open(inv["image"], "rb") as f:
    pos = gap_end
    while pos > visible_end:
        take = min(chunk, pos - visible_end)
        pos -= take
        data = read_extents(f, b["extents"], pos, take)
        stripped = data.rstrip(b"\x00")
        if stripped:
            last = pos + len(stripped) - 1
            break

extra_nonzero = None if last is None else last + 1 - visible_end
zero_to_moov = gap_end - (last + 1 if last is not None else visible_end)
print(json.dumps({
    "path": path,
    "visible_payload_end_estimate": visible_end,
    "moov_offset": gap_end,
    "last_nonzero_before_moov": last,
    "extra_nonzero_bytes_after_visible_samples": extra_nonzero,
    "zero_bytes_after_extra_before_moov": zero_to_moov,
    "video_seconds": video["mdhd_seconds"],
    "video_samples": video["stsz_sample_count"],
    "video_payload_bytes": video["stsz_sample_bytes_total"],
    "video_payload_bytes_per_second": video["stsz_sample_bytes_total"] / video["mdhd_seconds"],
    "extra_nonzero_seconds_at_visible_rate": None if extra_nonzero is None else extra_nonzero / (video["stsz_sample_bytes_total"] / video["mdhd_seconds"]),
}, ensure_ascii=False, indent=2))
