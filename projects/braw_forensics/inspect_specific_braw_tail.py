#!/usr/bin/env python3
import argparse
import json
import os


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


def window_stats(read_at, start, total, step):
    rows = []
    pos = 0
    pats = [b"mdat", b"moov", b"braw", b"Blackmagic"]
    while pos < total:
        take = min(step, total - pos)
        data = read_at(start + pos, take)
        if not data:
            break
        rows.append({
            "rel_offset": start + pos,
            "size": len(data),
            "zero_fraction": data.count(0) / len(data),
            "hits": {p.decode(): data.count(p) for p in pats},
        })
        pos += take
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory_json")
    ap.add_argument("track_json")
    ap.add_argument("path")
    ap.add_argument("--after-mib", type=int, default=2048)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    inv = json.load(open(args.inventory_json, encoding="utf-8"))
    tracks = json.load(open(args.track_json, encoding="utf-8"))
    b = next(x for x in inv["braws"] if x["path"] == args.path)
    tr = next(x for x in tracks if x["path"] == args.path)
    video = tr["tracks"][0]
    mdat = next(x for x in b["top_boxes"] if x["type"] == "mdat")
    moov = next(x for x in b["top_boxes"] if x["type"] == "moov")
    visible_payload_end = 8 + video["stsz_sample_bytes_total"]
    suspect_len = max(0, moov["offset"] - visible_payload_end)
    file_end = max(e["image_offset"] + e["byte_count"] for e in b["extents"])

    with open(inv["image"], "rb") as img:
        def read_file(rel, n):
            return read_extents(img, b["extents"], rel, n)

        suspect_windows = window_stats(read_file, visible_payload_end, suspect_len, 16 * 1024 * 1024)

        after = []
        img.seek(file_end)
        total_after = min(args.after_mib * 1024 * 1024, inv["image_size"] - file_end)
        pos = 0
        while pos < total_after:
            take = min(16 * 1024 * 1024, total_after - pos)
            img.seek(file_end + pos)
            data = img.read(take)
            if not data:
                break
            after.append({
                "rel_after_eof": pos,
                "abs_offset": file_end + pos,
                "size": len(data),
                "zero_fraction": data.count(0) / len(data),
                "hits": {p.decode(): data.count(p) for p in [b"mdat", b"moov", b"braw", b"Blackmagic"]},
            })
            pos += take

    result = {
        "path": args.path,
        "logical_size": b["logical_size"],
        "file_start": b["extents"][0]["image_offset"],
        "file_end": file_end,
        "mdat_size": mdat["size"],
        "moov_offset": moov["offset"],
        "moov_size": moov["size"],
        "video_samples": video["stsz_sample_count"],
        "video_seconds": video["mdhd_seconds"],
        "video_payload_bytes": video["stsz_sample_bytes_total"],
        "visible_payload_end_estimate": visible_payload_end,
        "suspect_gap_before_moov": suspect_len,
        "suspect_gap_summary": {
            "windows": len(suspect_windows),
            "all_zero_windows": sum(1 for r in suspect_windows if r["zero_fraction"] == 1.0),
            "nonzero_windows": sum(1 for r in suspect_windows if r["zero_fraction"] != 1.0),
            "min_zero_fraction": min((r["zero_fraction"] for r in suspect_windows), default=None),
            "max_zero_fraction": max((r["zero_fraction"] for r in suspect_windows), default=None),
            "signature_hits": {
                k: sum(r["hits"][k] for r in suspect_windows)
                for k in ["mdat", "moov", "braw", "Blackmagic"]
            },
        },
        "suspect_gap_windows_first_20": suspect_windows[:20],
        "suspect_gap_windows_last_20": suspect_windows[-20:],
        "after_eof_summary": {
            "scanned_bytes": total_after,
            "windows": len(after),
            "all_zero_windows": sum(1 for r in after if r["zero_fraction"] == 1.0),
            "nonzero_windows": sum(1 for r in after if r["zero_fraction"] != 1.0),
            "signature_hits": {
                k: sum(r["hits"][k] for r in after)
                for k in ["mdat", "moov", "braw", "Blackmagic"]
            },
        },
        "after_eof_interesting": [r for r in after if r["zero_fraction"] != 1.0 or any(r["hits"].values())][:40],
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
