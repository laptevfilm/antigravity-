#!/usr/bin/env python3
import json
import sys


inv = json.load(open(sys.argv[1], encoding="utf-8"))
limit_gib = int(sys.argv[2])
out = sys.argv[3]
b = inv["braws"][-1]
end = max(e["image_offset"] + e["byte_count"] for e in b["extents"])
total = min(limit_gib * 1024**3, inv["image_size"] - end)
pats = [b"mdat", b"moov", b"braw", b"Blackmagic"]
chunk = 4 * 1024**2
hits = {p.decode(): 0 for p in pats}
first = None
interesting = []
zero_windows = 0
nonzero_windows = 0

with open(inv["image"], "rb") as f:
    pos = 0
    while pos < total:
        take = min(chunk, total - pos)
        f.seek(end + pos)
        data = f.read(take)
        z = data.count(0)
        nz = len(data) - z
        local = {p.decode(): data.count(p) for p in pats}
        for k, v in local.items():
            hits[k] += v
        if nz:
            nonzero_windows += 1
            if first is None:
                first = {"rel": pos, "abs": end + pos, "zero_fraction": z / len(data)}
        else:
            zero_windows += 1
        if nz or any(local.values()):
            interesting.append({"rel": pos, "abs": end + pos, "zero_fraction": z / len(data), "hits": local})
        pos += take

result = {
    "path": b["path"],
    "file_end": end,
    "scanned_bytes": total,
    "window_size": chunk,
    "windows": (total + chunk - 1) // chunk,
    "all_zero_windows": zero_windows,
    "nonzero_windows": nonzero_windows,
    "first_nonzero": first,
    "hits": hits,
    "interesting_count": len(interesting),
    "interesting_first_40": interesting[:40],
}
json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
