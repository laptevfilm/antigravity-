#!/usr/bin/env python3
import argparse
import json
import os


CHUNK = 1024 * 1024


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


def last_nonzero_before(f, braw, limit):
    pos = limit
    zero_tail = 0
    while pos > 0:
        take = min(CHUNK, pos)
        pos -= take
        data = read_extents(f, braw["extents"], pos, take)
        idx = data.rstrip(b"\x00")
        if idx:
            return pos + len(idx) - 1, zero_tail + (take - len(idx))
        zero_tail += take
    return None, zero_tail


def window_stats(f, start, total, step=CHUNK):
    rows = []
    pos = 0
    while pos < total:
        take = min(step, total - pos)
        f.seek(start + pos)
        data = f.read(take)
        if not data:
            break
        rows.append({
            "rel_offset": pos,
            "abs_offset": start + pos,
            "size": len(data),
            "zero_fraction": data.count(0) / len(data),
            "hits": {s: data.count(s.encode("ascii")) for s in ["mdat", "moov", "braw", "Blackmagic", "free", "wide"]},
        })
        pos += take
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory_json")
    ap.add_argument("--after-mib", type=int, default=1024)
    ap.add_argument("--out", default="braw_forensics/deep_tail_scan.json")
    args = ap.parse_args()
    with open(args.inventory_json, "r", encoding="utf-8") as f:
        inv = json.load(f)
    results = []
    with open(inv["image"], "rb") as img:
        for b in inv["braws"]:
            moov = next((x for x in b["top_boxes"] if x["type"] == "moov" and x["valid"]), None)
            mdat = next((x for x in b["top_boxes"] if x["type"] == "mdat" and x["valid"]), None)
            limit = moov["offset"] if moov else b["logical_size"]
            last_nz, zeros = last_nonzero_before(img, b, limit)
            file_end = max(e["image_offset"] + e["byte_count"] for e in b["extents"])
            after = window_stats(img, file_end, min(args.after_mib * CHUNK, max(0, inv["image_size"] - file_end)))
            results.append({
                "path": b["path"],
                "logical_size": b["logical_size"],
                "mdat_size": mdat["size"] if mdat else None,
                "moov_offset": moov["offset"] if moov else None,
                "moov_size": moov["size"] if moov else None,
                "last_nonzero_before_moov": last_nz,
                "zero_bytes_before_moov": zeros,
                "file_end_abs": file_end,
                "after_file_first_64m": after[:64],
                "after_file_summary": {
                    "windows": len(after),
                    "all_zero_windows": sum(1 for r in after if r["zero_fraction"] == 1.0),
                    "nonzero_windows": sum(1 for r in after if r["zero_fraction"] != 1.0),
                    "signature_hits": {
                        k: sum(r["hits"][k] for r in after)
                        for k in ["mdat", "moov", "braw", "Blackmagic", "free", "wide"]
                    },
                    "first_nonzero_window": next((r for r in after if r["zero_fraction"] != 1.0), None),
                },
                "after_file_nonzero_or_signature_windows": [
                    r for r in after
                    if r["zero_fraction"] != 1.0 or any(r["hits"].values())
                ]
            })
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results[-1], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
