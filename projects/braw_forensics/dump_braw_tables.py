#!/usr/bin/env python3
import json
import struct
import sys


def u32(b, o): return struct.unpack_from(">I", b, o)[0]
def u64(b, o): return struct.unpack_from(">Q", b, o)[0]


CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "tref", "dinf", "udta", "meta"}


def boxes(buf, start, end, path=""):
    p = start
    while p + 8 <= end:
        sz = u32(buf, p)
        typ = buf[p+4:p+8].decode("latin-1", "replace")
        hdr = 8
        if sz == 1:
            sz = u64(buf, p+8); hdr = 16
        elif sz == 0:
            sz = end - p
        if sz < hdr or p + sz > end:
            break
        cur = f"{path}/{typ}" if path else typ
        yield cur, p, sz, hdr
        child = p + hdr + (4 if typ == "meta" else 0)
        if typ in CONTAINERS and child < p + sz:
            yield from boxes(buf, child, p + sz, cur)
        p += sz


def read_file(path, off, size):
    with open(path, "rb") as f:
        f.seek(off)
        return f.read(size)


def parse_stsz(buf, body):
    sample_size = u32(buf, body + 4)
    count = u32(buf, body + 8)
    if sample_size:
        sizes = [sample_size] * count
    else:
        sizes = [u32(buf, body + 12 + i * 4) for i in range(count)]
    return sample_size, sizes


def parse_table(buf, typ, body):
    if typ == "stts":
        n = u32(buf, body + 4)
        return [(u32(buf, body + 8 + i*8), u32(buf, body + 12 + i*8)) for i in range(n)]
    if typ == "stsc":
        n = u32(buf, body + 4)
        return [(u32(buf, body + 8 + i*12), u32(buf, body + 12 + i*12), u32(buf, body + 16 + i*12)) for i in range(n)]
    if typ == "stco":
        n = u32(buf, body + 4)
        return [u32(buf, body + 8 + i*4) for i in range(n)]
    if typ == "co64":
        n = u32(buf, body + 4)
        return [u64(buf, body + 8 + i*8) for i in range(n)]
    return None


def main():
    braw = sys.argv[1]
    out = sys.argv[2]
    with open(braw, "rb") as f:
        head = f.read(16)
        mdat_size = u32(head, 0)
        if head[4:8] != b"mdat":
            raise SystemExit("not mdat-first braw")
        if mdat_size == 1:
            mdat_size = u64(head, 8)
        f.seek(mdat_size)
        moov_head = f.read(8)
        moov_size = u32(moov_head, 0)
        if moov_head[4:8] != b"moov":
            raise SystemExit("moov not found at mdat end")
        f.seek(mdat_size)
        moov = f.read(moov_size)
    tracks = []
    for path, p, sz, hdr in boxes(moov, 8, len(moov)):
        if path != "trak":
            continue
        trbuf = moov[p:p+sz]
        tr = {"trak_offset_in_moov": p, "trak_size": sz, "boxes": []}
        for spath, q, ssz, sh in boxes(trbuf, 8, len(trbuf), "trak"):
            typ = spath.rsplit("/", 1)[-1]
            if typ in {"tkhd", "mdhd", "stsd", "stts", "stsc", "stsz", "stco", "co64"}:
                body = q + sh
                rec = {"path": spath, "offset_in_trak": q, "size": ssz}
                if typ == "tkhd":
                    rec["duration"] = u32(trbuf, body + 20)
                    rec["track_id"] = u32(trbuf, body + 12)
                elif typ == "mdhd":
                    rec["timescale"] = u32(trbuf, body + 12)
                    rec["duration"] = u32(trbuf, body + 16)
                elif typ == "stsd":
                    rec["entry_count"] = u32(trbuf, body + 4)
                    if rec["entry_count"]:
                        rec["sample_entry_type"] = trbuf[body+16:body+20].decode("latin-1", "replace")
                elif typ == "stsz":
                    sample_size, sizes = parse_stsz(trbuf, body)
                    rec["sample_size"] = sample_size
                    rec["count"] = len(sizes)
                    rec["sum"] = sum(sizes)
                    rec["first10"] = sizes[:10]
                    rec["last20"] = sizes[-20:]
                    rec["min"] = min(sizes) if sizes else None
                    rec["max"] = max(sizes) if sizes else None
                elif typ in {"stts", "stsc", "stco", "co64"}:
                    table = parse_table(trbuf, typ, body)
                    rec["count"] = len(table)
                    rec["first10"] = table[:10]
                    rec["last10"] = table[-10:]
                tr["boxes"].append(rec)
        tracks.append(tr)
    result = {"file": braw, "mdat_size": mdat_size, "moov_size": moov_size, "tracks": tracks}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
