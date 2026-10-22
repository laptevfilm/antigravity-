#!/usr/bin/env python3
import json
import os
import struct
import sys


def be32(b, o): return struct.unpack_from(">I", b, o)[0]
def be64(b, o): return struct.unpack_from(">Q", b, o)[0]


CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "tref", "dinf", "udta", "meta"}


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


def walk_boxes(buf, start, end, path=""):
    pos = start
    while pos + 8 <= end:
        size = be32(buf, pos)
        typ = buf[pos + 4:pos + 8].decode("latin-1", errors="replace")
        hdr = 8
        if size == 1:
            if pos + 16 > end:
                break
            size = be64(buf, pos + 8)
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr or pos + size > end:
            break
        cur = f"{path}/{typ}" if path else typ
        yield cur, pos, size, hdr
        child_start = pos + hdr
        if typ == "meta":
            child_start += 4
        if typ in CONTAINERS and child_start < pos + size:
            yield from walk_boxes(buf, child_start, pos + size, cur)
        pos += size


def main():
    inv_path = sys.argv[1]
    out_path = sys.argv[2]
    inv = json.load(open(inv_path, encoding="utf-8"))
    rows = []
    with open(inv["image"], "rb") as img:
        for b in inv["braws"]:
            moov = next(x for x in b["top_boxes"] if x["type"] == "moov")
            mdat = next(x for x in b["top_boxes"] if x["type"] == "mdat")
            moov_data = read_extents(img, b["extents"], moov["offset"], moov["size"])
            row = {
                "path": b["path"],
                "logical_size": b["logical_size"],
                "mdat_size": mdat["size"],
                "moov_size": moov["size"],
                "timescale": None,
                "duration_units": None,
                "duration_seconds": None,
                "stsz_sample_count": None,
                "stsz_sum": None,
                "box_types": [],
            }
            for path, off, size, hdr in walk_boxes(moov_data, 0, len(moov_data)):
                typ = path.rsplit("/", 1)[-1]
                if typ not in row["box_types"]:
                    row["box_types"].append(typ)
                body = off + hdr
                if typ == "mvhd":
                    version = moov_data[body]
                    if version == 0:
                        row["timescale"] = be32(moov_data, body + 12)
                        row["duration_units"] = be32(moov_data, body + 16)
                    elif version == 1:
                        row["timescale"] = be32(moov_data, body + 20)
                        row["duration_units"] = be64(moov_data, body + 24)
                    if row["timescale"]:
                        row["duration_seconds"] = row["duration_units"] / row["timescale"]
                if typ == "stsz":
                    sample_size = be32(moov_data, body + 4)
                    count = be32(moov_data, body + 8)
                    row["stsz_sample_count"] = count
                    if sample_size:
                        row["stsz_sum"] = sample_size * count
                    else:
                        row["stsz_sum"] = sum(be32(moov_data, body + 12 + i * 4) for i in range(count))
            if row["duration_seconds"]:
                row["logical_bytes_per_second"] = b["logical_size"] / row["duration_seconds"]
                row["mdat_bytes_per_second"] = mdat["size"] / row["duration_seconds"]
                row["stsz_bytes_per_second"] = row["stsz_sum"] / row["duration_seconds"] if row["stsz_sum"] is not None else None
            rows.append(row)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(rows, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in rows:
        print(f"{r['path']}: duration={r['duration_seconds']}s samples={r['stsz_sample_count']} logical={r['logical_size']} stsz_sum={r['stsz_sum']} Bps={r.get('stsz_bytes_per_second')}")


if __name__ == "__main__":
    main()
