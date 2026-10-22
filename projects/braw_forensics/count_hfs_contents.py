#!/usr/bin/env python3
import argparse
import csv
import os
from analyze_hfs_braw import HFSImage, catalog_records, build_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--part-offset", type=lambda x: int(x, 0), default=8192 * 512)
    ap.add_argument("--out", default="braw_forensics")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    img = HFSImage(args.image, args.part_offset)
    records = [rec for _, rec in catalog_records(img)]
    paths = build_paths(records)
    files = [r for r in records if r.get("type") == "file"]
    folders = [r for r in records if r.get("type") == "folder"]
    braws = [r for r in files if r["name"].lower().endswith(".braw")]

    csv_path = os.path.join(args.out, "hfs_file_list.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "id", "path", "logical_size", "content_mod_date"])
        for r in files:
            fork = r.get("data_fork") or {}
            w.writerow([r.get("type"), r.get("id"), paths.get(r.get("id"), r["name"]),
                        fork.get("logical_size"), r.get("content_mod_date")])

    print(f"catalog_records={len(records)}")
    print(f"folders={len(folders)}")
    print(f"files={len(files)}")
    print(f"braw_files={len(braws)}")
    print(f"file_list_csv={csv_path}")
    print("braw_names:")
    for r in braws:
        fork = r.get("data_fork") or {}
        print(f"  {paths.get(r.get('id'), r['name'])}\t{fork.get('logical_size')}")
    img.close()


if __name__ == "__main__":
    main()
