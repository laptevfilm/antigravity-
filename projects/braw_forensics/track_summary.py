#!/usr/bin/env python3
import json
import os
import struct
import sys


def be32(b, o): return struct.unpack_from(">I", b, o)[0]
def be64(b, o): return struct.unpack_from(">Q", b, o)[0]


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


def children(buf, start, end):
    pos = start
    while pos + 8 <= end:
        size = be32(buf, pos)
        typ = buf[pos + 4:pos + 8].decode("latin-1", errors="replace")
        hdr = 8
        if size == 1:
            size = be64(buf, pos + 8)
            hdr = 16
        elif size == 0:
            size = end - pos
        if size < hdr or pos + size > end:
            break
        yield typ, pos, size, hdr
        pos += size


def find_boxes(buf, start, end, wanted):
    for typ, pos, size, hdr in children(buf, start, end):
        if typ in wanted:
            yield typ, pos, size, hdr
        if typ in {"trak", "mdia", "minf", "stbl", "edts", "tref", "dinf"}:
            yield from find_boxes(buf, pos + hdr, pos + size, wanted)


def box_value_summary(buf, typ, pos, hdr):
    body = pos + hdr
    if typ in {"mvhd", "tkhd", "mdhd"}:
        version = buf[body]
        if typ == "mvhd":
            if version == 0:
                return {"timescale": be32(buf, body + 12), "duration": be32(buf, body + 16)}
            return {"timescale": be32(buf, body + 20), "duration": be64(buf, body + 24)}
        if typ == "tkhd":
            if version == 0:
                return {"track_id": be32(buf, body + 12), "duration": be32(buf, body + 20)}
            return {"track_id": be32(buf, body + 20), "duration": be64(buf, body + 28)}
        if typ == "mdhd":
            if version == 0:
                return {"timescale": be32(buf, body + 12), "duration": be32(buf, body + 16)}
            return {"timescale": be32(buf, body + 20), "duration": be64(buf, body + 24)}
    if typ == "hdlr":
        return {"handler": buf[body + 8:body + 12].decode("latin-1", errors="replace")}
    if typ == "stsz":
        sample_size = be32(buf, body + 4)
        count = be32(buf, body + 8)
        total = sample_size * count if sample_size else sum(be32(buf, body + 12 + i * 4) for i in range(count))
        return {"sample_size": sample_size, "sample_count": count, "sample_bytes_total": total}
    return {}


def main():
    inv = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    rows = []
    with open(inv["image"], "rb") as img:
        for b in inv["braws"]:
            moov = next(x for x in b["top_boxes"] if x["type"] == "moov")
            data = read_extents(img, b["extents"], moov["offset"], moov["size"])
            mvhd = next((box_value_summary(data, t, p, h) for t, p, s, h in children(data, 8, len(data)) if t == "mvhd"), {})
            tracks = []
            for typ, pos, size, hdr in children(data, 8, len(data)):
                if typ != "trak":
                    continue
                tr = {"track_id": None, "handler": None, "tkhd_duration": None, "mdhd_timescale": None,
                      "mdhd_duration": None, "stsz_sample_count": None, "stsz_sample_bytes_total": None}
                for t, p, s, h in find_boxes(data, pos + hdr, pos + size, {"tkhd", "mdhd", "hdlr", "stsz"}):
                    val = box_value_summary(data, t, p, h)
                    if t == "tkhd":
                        tr["track_id"] = val.get("track_id")
                        tr["tkhd_duration"] = val.get("duration")
                    elif t == "mdhd":
                        tr["mdhd_timescale"] = val.get("timescale")
                        tr["mdhd_duration"] = val.get("duration")
                    elif t == "hdlr":
                        tr["handler"] = val.get("handler")
                    elif t == "stsz":
                        tr["stsz_sample_count"] = val.get("sample_count")
                        tr["stsz_sample_bytes_total"] = val.get("sample_bytes_total")
                if tr["mdhd_timescale"]:
                    tr["mdhd_seconds"] = tr["mdhd_duration"] / tr["mdhd_timescale"]
                tracks.append(tr)
            rows.append({"path": b["path"], "mvhd": mvhd, "tracks": tracks})
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in rows:
        print(r["path"], r["mvhd"])
        for tr in r["tracks"]:
            print(" ", tr)


if __name__ == "__main__":
    main()
