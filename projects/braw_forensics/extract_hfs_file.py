#!/usr/bin/env python3
import argparse
import os
import sys
from analyze_hfs_braw import HFSImage, catalog_records, build_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("hfs_path")
    ap.add_argument("output")
    ap.add_argument("--part-offset", type=lambda x: int(x, 0), default=8192 * 512)
    args = ap.parse_args()

    img = HFSImage(args.image, args.part_offset)
    records = [rec for _, rec in catalog_records(img)]
    paths = build_paths(records)
    target = None
    want = args.hfs_path.replace("\\", "/")
    for rec in records:
        if rec.get("type") == "file" and paths.get(rec.get("id"), rec.get("name")) == want:
            target = rec
            break
    if target is None:
        raise SystemExit(f"File not found in HFS+ catalog: {args.hfs_path}")

    fork = target["data_fork"]
    logical_size = fork["logical_size"]
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    if os.path.exists(args.output) and os.path.getsize(args.output) == logical_size:
        print(f"Already extracted: {args.output} ({logical_size} bytes)")
        return

    copied = 0
    chunk = 16 * 1024 * 1024
    with open(args.output, "wb") as out:
        for extent in fork["extents"]:
            remaining = min(extent["block_count"] * img.block_size, logical_size - copied)
            src = img.abs_for_block(extent["start_block"])
            while remaining > 0:
                take = min(chunk, remaining)
                data = img.read_abs(src, take)
                if not data:
                    raise RuntimeError("Unexpected EOF while reading image")
                out.write(data)
                src += len(data)
                copied += len(data)
                remaining -= len(data)
                if copied % (1024 * 1024 * 1024) < chunk:
                    print(f"{copied}/{logical_size} bytes", flush=True)
            if copied >= logical_size:
                break
    img.close()
    print(f"Extracted: {args.output} ({copied} bytes)")


if __name__ == "__main__":
    main()
