from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
import struct


_HFS_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class HfsBrawFile:
    path: str
    logical_size: int
    create_date: str | None
    content_mod_date: str | None
    extents: list[dict[str, int]]
    id: int


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def _u64(data: bytes, offset: int) -> int:
    return struct.unpack_from(">Q", data, offset)[0]


def _hfs_time(value: int) -> str | None:
    if not value:
        return None
    try:
        return (_HFS_EPOCH + timedelta(seconds=value)).isoformat()
    except OverflowError:
        return None


def _parse_extents(data: bytes, offset: int) -> list[dict[str, int]]:
    return [
        {"start_block": _u32(data, offset + index * 8), "block_count": _u32(data, offset + index * 8 + 4)}
        for index in range(8)
        if _u32(data, offset + index * 8 + 4)
    ]


def _parse_fork(data: bytes, offset: int) -> dict[str, int | list[dict[str, int]]]:
    return {
        "logical_size": _u64(data, offset),
        "total_blocks": _u32(data, offset + 12),
        "extents": _parse_extents(data, offset + 16),
    }


def _require_inline_extents(fork: dict[str, int | list[dict[str, int]]]) -> None:
    extents = fork["extents"]
    assert isinstance(extents, list)
    inline_blocks = sum(extent["block_count"] for extent in extents)
    if fork["total_blocks"] > inline_blocks:
        raise ValueError("extents overflow parsing not implemented")


class _HfsImage:
    def __init__(self, path: Path, part_offset: int) -> None:
        self.path = path
        self.part_offset = part_offset
        self.file = path.open("rb")
        self.file.seek(part_offset + 1024)
        self.volume_header = self.file.read(512)
        if len(self.volume_header) != 512 or self.volume_header[:2] not in (b"H+", b"HX"):
            self.file.close()
            raise ValueError(f"no HFS+ volume header at {part_offset + 1024}")
        self.block_size = _u32(self.volume_header, 40)
        if not self.block_size:
            self.file.close()
            raise ValueError("HFS+ allocation block size is zero")
        self.catalog_fork = _parse_fork(self.volume_header, 272)
        _require_inline_extents(self.catalog_fork)

    def close(self) -> None:
        self.file.close()

    def __enter__(self) -> _HfsImage:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _absolute_block_offset(self, block: int) -> int:
        return self.part_offset + block * self.block_size

    def read_absolute(self, offset: int, size: int) -> bytes:
        self.file.seek(offset)
        data = self.file.read(size)
        if len(data) != size:
            raise ValueError("unexpected EOF while reading card image")
        return data

    def read_fork(self, fork: dict[str, int | list[dict[str, int]]], offset: int, size: int) -> bytes:
        logical_size = fork["logical_size"]
        assert isinstance(logical_size, int)
        if offset < 0 or size < 0 or offset + size > logical_size:
            raise ValueError("fork read exceeds logical size")
        _require_inline_extents(fork)
        extents = fork["extents"]
        assert isinstance(extents, list)
        result = bytearray()
        remaining = size
        position = offset
        for extent in extents:
            extent_size = extent["block_count"] * self.block_size
            if position >= extent_size:
                position -= extent_size
                continue
            take = min(remaining, extent_size - position)
            result.extend(self.read_absolute(self._absolute_block_offset(extent["start_block"]) + position, take))
            remaining -= take
            position = 0
            if not remaining:
                return bytes(result)
        raise ValueError("extents overflow parsing not implemented")

    def extent_payload(self, fork: dict[str, int | list[dict[str, int]]]) -> list[dict[str, int]]:
        _require_inline_extents(fork)
        extents = fork["extents"]
        assert isinstance(extents, list)
        return [
            {
                **extent,
                "image_offset": self._absolute_block_offset(extent["start_block"]),
                "byte_count": extent["block_count"] * self.block_size,
            }
            for extent in extents
        ]


def _catalog_key(node: bytes, offset: int) -> tuple[int, str, int]:
    if offset + 8 > len(node):
        raise ValueError("truncated HFS+ catalog key")
    key_length = _u16(node, offset)
    key_end = offset + 2 + key_length
    if key_length < 6 or key_end > len(node):
        raise ValueError("invalid HFS+ catalog key")
    parent_id = _u32(node, offset + 2)
    name_length = _u16(node, offset + 6)
    name_end = offset + 8 + name_length * 2
    if name_end > key_end:
        raise ValueError("invalid HFS+ catalog name")
    name = node[offset + 8:name_end].decode("utf-16-be", errors="replace")
    record_offset = key_end + (key_end % 2)
    return parent_id, name, record_offset


def _catalog_record(node: bytes, offset: int) -> dict[str, object]:
    if offset + 20 > len(node):
        raise ValueError("truncated HFS+ catalog record")
    record_type = struct.unpack_from(">h", node, offset)[0]
    if record_type == 1:
        return {"type": "folder", "id": _u32(node, offset + 8)}
    if record_type != 2:
        return {"type": f"record_{record_type}"}
    if offset + 168 > len(node):
        raise ValueError("truncated HFS+ file record")
    return {
        "type": "file",
        "id": _u32(node, offset + 8),
        "create_date": _hfs_time(_u32(node, offset + 12)),
        "content_mod_date": _hfs_time(_u32(node, offset + 16)),
        "data_fork": _parse_fork(node, offset + 88),
    }


def _catalog_records(image: _HfsImage) -> list[dict[str, object]]:
    header = image.read_fork(image.catalog_fork, 0, 512)
    if len(header) < 36:
        raise ValueError("truncated HFS+ catalog B-tree header")
    first_leaf = _u32(header, 24)
    node_size = _u16(header, 32)
    if not node_size:
        raise ValueError("HFS+ catalog B-tree node size is zero")
    records: list[dict[str, object]] = []
    seen: set[int] = set()
    node_number = first_leaf
    while node_number and node_number not in seen:
        seen.add(node_number)
        node = image.read_fork(image.catalog_fork, node_number * node_size, node_size)
        next_leaf = _u32(node, 0)
        kind = struct.unpack_from(">b", node, 8)[0]
        record_count = _u16(node, 10)
        if kind != -1:
            raise ValueError("unexpected HFS+ catalog B-tree node kind")
        if record_count * 2 > node_size - 14:
            raise ValueError("invalid HFS+ catalog B-tree record count")
        offsets = [_u16(node, node_size - 2 * (index + 1)) for index in range(record_count)]
        for offset in offsets:
            parent_id, name, record_offset = _catalog_key(node, offset)
            records.append({"parent_id": parent_id, "name": name, **_catalog_record(node, record_offset)})
        node_number = next_leaf
    return records


def _paths(records: list[dict[str, object]]) -> dict[int, str]:
    by_id = {record["id"]: record for record in records if record.get("type") in {"folder", "file"}}
    paths: dict[int, str] = {}
    for record in records:
        if record.get("type") != "file":
            continue
        parts = [str(record["name"])]
        parent = record["parent_id"]
        for _ in range(100):
            if parent == 2 or parent not in by_id:
                break
            parent_record = by_id[parent]
            parts.append(str(parent_record["name"]))
            parent = parent_record["parent_id"]
        paths[int(record["id"])] = "/" + "/".join(reversed(parts))
    return paths


def inventory_braw_files(image_path: Path, part_offset: int = 0) -> list[HfsBrawFile]:
    with _HfsImage(image_path, part_offset) as image:
        records = _catalog_records(image)
        paths = _paths(records)
        files: list[HfsBrawFile] = []
        for record in records:
            if record.get("type") != "file" or not str(record["name"]).lower().endswith(".braw"):
                continue
            fork = record["data_fork"]
            assert isinstance(fork, dict)
            _require_inline_extents(fork)
            logical_size = fork["logical_size"]
            assert isinstance(logical_size, int)
            files.append(HfsBrawFile(paths.get(int(record["id"]), str(record["name"])), logical_size, record["create_date"], record["content_mod_date"], image.extent_payload(fork), int(record["id"])))
    return sorted(files, key=lambda file: (file.content_mod_date or "", file.id))


def _extraction_filename(catalog_path: str) -> str:
    normalized_path = catalog_path.replace("\\", "/")
    windows_path = PureWindowsPath(catalog_path)
    if windows_path.drive or normalized_path.startswith("//"):
        raise ValueError("invalid HFS+ file path")

    components = normalized_path.split("/")
    if any(component in {".", ".."} for component in components):
        raise ValueError("invalid HFS+ file path")
    for component in components:
        if not component:
            continue
        if (
            any(ord(character) < 32 for character in component)
            or any(character in '<>:"|?*' for character in component)
            or component[-1] in ". "
        ):
            raise ValueError("invalid HFS+ file path")
        device_name = component.rstrip(". ").split(".", 1)[0].upper()
        if device_name in {"CON", "PRN", "AUX", "NUL"} or device_name in {
            *(f"COM{index}" for index in range(1, 10)),
            *(f"LPT{index}" for index in range(1, 10)),
        }:
            raise ValueError("invalid HFS+ file path")

    filename = PurePosixPath(normalized_path).name
    if not filename:
        raise ValueError("invalid HFS+ file path")
    return filename


def extract_braw_file(image_path: Path, target: HfsBrawFile, out_dir: Path) -> Path:
    filename = _extraction_filename(target.path)
    destination = out_dir / filename
    out_dir_resolved = out_dir.resolve()
    destination_resolved = destination.resolve()
    try:
        destination_resolved.relative_to(out_dir_resolved)
    except ValueError:
        raise ValueError("output path escapes output directory") from None
    if destination.resolve() == image_path.resolve():
        raise ValueError("output path is the same as source")
    if destination.exists():
        raise ValueError(f"output file already exists: {destination}")
    out_dir.mkdir(parents=True, exist_ok=True)
    remaining = target.logical_size
    created = False
    try:
        with image_path.open("rb") as source, destination.open("xb") as output:
            created = True
            for extent in target.extents:
                if remaining <= 0:
                    break
                byte_count = int(extent["byte_count"])
                take = min(remaining, byte_count)
                source.seek(int(extent["image_offset"]))
                while take:
                    chunk = source.read(min(take, 16 * 1024 * 1024))
                    if not chunk:
                        raise ValueError("unexpected EOF while reading card image")
                    output.write(chunk)
                    take -= len(chunk)
                    remaining -= len(chunk)
        if remaining:
            raise ValueError("extents overflow parsing not implemented")
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return destination
