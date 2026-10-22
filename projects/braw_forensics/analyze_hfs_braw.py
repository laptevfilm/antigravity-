#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import struct
from datetime import datetime, timezone, timedelta


HFS_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


def be16(b, o): return struct.unpack_from(">H", b, o)[0]
def be32(b, o): return struct.unpack_from(">I", b, o)[0]
def be64(b, o): return struct.unpack_from(">Q", b, o)[0]


def hfs_time(v):
    if not v:
        return None
    try:
        return (HFS_EPOCH + timedelta(seconds=v)).isoformat()
    except OverflowError:
        return None


def parse_extents(b, o):
    return [{"start_block": be32(b, o + i * 8), "block_count": be32(b, o + i * 8 + 4)}
            for i in range(8) if be32(b, o + i * 8 + 4)]


def parse_fork(b, o):
    return {
        "logical_size": be64(b, o),
        "clump_size": be32(b, o + 8),
        "total_blocks": be32(b, o + 12),
        "extents": parse_extents(b, o + 16),
    }


class HFSImage:
    def __init__(self, path, part_offset):
        self.f = open(path, "rb")
        self.path = path
        self.part_offset = part_offset
        self.f.seek(part_offset + 1024)
        self.vh = self.f.read(512)
        if self.vh[:2] not in (b"H+", b"HX"):
            raise SystemExit(f"No HFS+ volume header at {part_offset + 1024}")
        self.block_size = be32(self.vh, 40)
        self.total_blocks = be32(self.vh, 44)
        self.catalog_fork = parse_fork(self.vh, 272)
        self.extents_fork = parse_fork(self.vh, 192)

    def close(self):
        self.f.close()

    def abs_for_block(self, block):
        return self.part_offset + block * self.block_size

    def read_abs(self, offset, size):
        self.f.seek(offset)
        return self.f.read(size)

    def read_fork(self, fork, offset, size):
        out = bytearray()
        remaining = size
        pos = offset
        for ex in fork["extents"]:
            ex_len = ex["block_count"] * self.block_size
            if pos >= ex_len:
                pos -= ex_len
                continue
            take = min(remaining, ex_len - pos)
            self.f.seek(self.abs_for_block(ex["start_block"]) + pos)
            out.extend(self.f.read(take))
            remaining -= take
            pos = 0
            if remaining == 0:
                break
        if remaining:
            raise RuntimeError("Fork read exceeded inline extents; extents overflow parsing not implemented")
        return bytes(out)


def utf16be_name(raw):
    n = be16(raw, 0)
    return raw[2:2 + n * 2].decode("utf-16-be", errors="replace")


def parse_catalog_key(buf, off):
    key_len = be16(buf, off)
    parent_id = be32(buf, off + 2)
    name = utf16be_name(buf[off + 6:off + 6 + key_len - 4])
    # Records are 2-byte aligned after the key.
    rec_off = off + 2 + key_len
    if rec_off & 1:
        rec_off += 1
    return parent_id, name, rec_off


def parse_catalog_record(buf, rec_off):
    rec_type = struct.unpack_from(">h", buf, rec_off)[0]
    if rec_type == 1:  # folder
        return {
            "type": "folder",
            "flags": be16(buf, rec_off + 2),
            "id": be32(buf, rec_off + 8),
            "create_date": hfs_time(be32(buf, rec_off + 12)),
            "content_mod_date": hfs_time(be32(buf, rec_off + 16)),
        }
    if rec_type == 2:  # file
        return {
            "type": "file",
            "flags": be16(buf, rec_off + 2),
            "id": be32(buf, rec_off + 8),
            "create_date": hfs_time(be32(buf, rec_off + 12)),
            "content_mod_date": hfs_time(be32(buf, rec_off + 16)),
            "data_fork": parse_fork(buf, rec_off + 88),
            "rsrc_fork": parse_fork(buf, rec_off + 168),
        }
    return {"type": f"record_{rec_type}"}


def catalog_records(img):
    header_node = img.read_fork(img.catalog_fork, 0, 512)
    # In a B-tree header node the header record starts immediately after the
    # 14-byte node descriptor; the record offset table is at the end of the
    # full node, whose size is only known after parsing this record.
    hdr_off = 14
    tree_depth = be16(header_node, hdr_off)
    root_node = be32(header_node, hdr_off + 2)
    leaf_records = be32(header_node, hdr_off + 6)
    first_leaf = be32(header_node, hdr_off + 10)
    last_leaf = be32(header_node, hdr_off + 14)
    node_size = be16(header_node, hdr_off + 18)
    total_nodes = be32(header_node, hdr_off + 22)
    info = {
        "tree_depth": tree_depth, "root_node": root_node, "leaf_records": leaf_records,
        "first_leaf": first_leaf, "last_leaf": last_leaf, "node_size": node_size,
        "total_nodes": total_nodes,
    }
    node = first_leaf
    seen = set()
    while node and node not in seen:
        seen.add(node)
        buf = img.read_fork(img.catalog_fork, node * node_size, node_size)
        f_link = be32(buf, 0)
        kind = struct.unpack_from(">b", buf, 8)[0]
        rec_count = be16(buf, 10)
        if kind != -1:
            break
        rec_offsets = [be16(buf, node_size - 2 * (i + 1)) for i in range(rec_count)]
        for off in rec_offsets:
            parent_id, name, rec_off = parse_catalog_key(buf, off)
            rec = parse_catalog_record(buf, rec_off)
            yield info, {"parent_id": parent_id, "name": name, **rec}
        node = f_link


def build_paths(records):
    names = {}
    for r in records:
        if r.get("type") in ("folder", "file"):
            names[r["id"]] = r["name"]
    paths = {}
    for r in records:
        if r.get("type") != "file":
            continue
        parts = [r["name"]]
        parent = r["parent_id"]
        guard = 0
        while parent in names and parent != 2 and guard < 100:
            parts.append(names[parent])
            parent = next((x["parent_id"] for x in records if x.get("type") == "folder" and x["id"] == parent), 2)
            guard += 1
        paths[r["id"]] = "/" + "/".join(reversed(parts))
    return paths


def top_boxes(read_at, size, limit=64):
    boxes = []
    pos = 0
    while pos + 8 <= size and len(boxes) < limit:
        hdr = read_at(pos, 16)
        if len(hdr) < 8:
            break
        sz = be32(hdr, 0)
        typ = hdr[4:8].decode("latin-1", errors="replace")
        hdr_len = 8
        if sz == 1 and len(hdr) >= 16:
            sz = be64(hdr, 8)
            hdr_len = 16
        elif sz == 0:
            sz = size - pos
        if sz < hdr_len or pos + sz > size:
            boxes.append({"offset": pos, "type": typ, "size": sz, "valid": False})
            break
        boxes.append({"offset": pos, "type": typ, "size": sz, "valid": True})
        pos += sz
    return boxes


def sample_stats(read_at, size, sample=1024 * 1024):
    chunks = []
    for label, off in [("head", 0), ("near_tail_64m", max(0, size - 64 * 1024 * 1024)), ("tail", max(0, size - sample))]:
        data = read_at(off, min(sample, size - off))
        chunks.append({
            "label": label,
            "offset": off,
            "size": len(data),
            "zero_fraction": data.count(0) / len(data) if data else None,
            "sha256_1m": hashlib.sha256(data).hexdigest() if data else None,
            "ascii_hits": {s: data.count(s.encode("ascii")) for s in ["ftyp", "mdat", "moov", "braw", "Blackmagic"]},
        })
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--part-offset", type=lambda x: int(x, 0), default=8192 * 512)
    ap.add_argument("--out", default="braw_forensics")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    img = HFSImage(args.image, args.part_offset)
    all_records = []
    btree_info = None
    for info, rec in catalog_records(img):
        btree_info = info
        all_records.append(rec)
    paths = build_paths(all_records)
    braws = []
    for r in all_records:
        if r.get("type") == "file" and r["name"].lower().endswith(".braw"):
            fork = r["data_fork"]
            extents = []
            for ex in fork["extents"]:
                extents.append({
                    **ex,
                    "image_offset": img.abs_for_block(ex["start_block"]),
                    "byte_count": ex["block_count"] * img.block_size,
                })
            def read_at(rel, n, fork=fork):
                return img.read_fork(fork, rel, n)
            braws.append({
                "id": r["id"],
                "path": paths.get(r["id"], r["name"]),
                "name": r["name"],
                "parent_id": r["parent_id"],
                "logical_size": fork["logical_size"],
                "allocated_bytes": fork["total_blocks"] * img.block_size,
                "create_date": r.get("create_date"),
                "content_mod_date": r.get("content_mod_date"),
                "extents": extents,
                "top_boxes": top_boxes(read_at, fork["logical_size"]),
                "samples": sample_stats(read_at, fork["logical_size"]),
            })
    braws.sort(key=lambda x: (x.get("content_mod_date") or "", x["id"]))
    summary = {
        "image": args.image,
        "image_size": os.path.getsize(args.image),
        "partition_offset": args.part_offset,
        "hfs_signature": img.vh[:2].decode("ascii"),
        "block_size": img.block_size,
        "total_blocks": img.total_blocks,
        "catalog_btree": btree_info,
        "braw_count": len(braws),
        "braws": braws,
    }
    json_path = os.path.join(args.out, "hfs_braw_inventory.json")
    csv_path = os.path.join(args.out, "hfs_braw_inventory.csv")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "path", "logical_size", "allocated_bytes", "create_date", "content_mod_date", "first_offset", "last_extent_end"])
        for b in braws:
            first = b["extents"][0]["image_offset"] if b["extents"] else None
            last = max((e["image_offset"] + e["byte_count"] for e in b["extents"]), default=None)
            w.writerow([b["id"], b["path"], b["logical_size"], b["allocated_bytes"], b["create_date"], b["content_mod_date"], first, last])
    print(json.dumps({
        "json": json_path, "csv": csv_path, "braw_count": len(braws),
        "last_braw": braws[-1] if braws else None,
    }, ensure_ascii=False, indent=2))
    img.close()


if __name__ == "__main__":
    main()
