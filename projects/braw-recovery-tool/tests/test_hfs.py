import json
from pathlib import Path

import pytest

import brawrec.cli as cli
from brawrec.cli import main
from brawrec.filesystem.hfs import HfsBrawFile, extract_braw_file, inventory_braw_files


def _fork(logical_size: int, total_blocks: int, start_block: int, block_count: int) -> bytes:
    value = bytearray(80)
    value[0:8] = logical_size.to_bytes(8, "big")
    value[12:16] = total_blocks.to_bytes(4, "big")
    value[16:20] = start_block.to_bytes(4, "big")
    value[20:24] = block_count.to_bytes(4, "big")
    return bytes(value)


def _hfs_image(path: Path, *, overflow: bool = False) -> bytes:
    block_size = 512
    image = bytearray(32 * block_size)
    header = memoryview(image)[1024:1536]
    header[0:2] = b"H+"
    header[40:44] = block_size.to_bytes(4, "big")
    header[44:48] = (32).to_bytes(4, "big")
    header[272:352] = _fork(1024, 2, 10, 2)

    btree_header = memoryview(image)[10 * block_size:11 * block_size]
    btree_header[14:16] = (1).to_bytes(2, "big")
    btree_header[20:24] = (1).to_bytes(4, "big")
    btree_header[24:28] = (1).to_bytes(4, "big")
    btree_header[32:34] = block_size.to_bytes(2, "big")

    name = "clip.braw".encode("utf-16-be")
    key_length = 6 + len(name)
    key = key_length.to_bytes(2, "big") + (2).to_bytes(4, "big") + (len(name) // 2).to_bytes(2, "big") + name
    record = bytearray(168)
    record[0:2] = (2).to_bytes(2, "big", signed=True)
    record[8:12] = (42).to_bytes(4, "big")
    record[12:16] = (1).to_bytes(4, "big")
    record[16:20] = (2).to_bytes(4, "big")
    record[88:168] = _fork(9, 2 if overflow else 1, 20, 1)
    leaf = memoryview(image)[11 * block_size:12 * block_size]
    leaf[8] = 0xFF
    leaf[10:12] = (1).to_bytes(2, "big")
    leaf[14:14 + len(key)] = key
    record_offset = 14 + len(key)
    if record_offset % 2:
        record_offset += 1
    leaf[record_offset:record_offset + len(record)] = record
    leaf[510:512] = (14).to_bytes(2, "big")
    image[20 * block_size:20 * block_size + 9] = b"BRAW DATA"
    path.write_bytes(image)
    return bytes(image)


def test_inventory_lists_inline_braw_file(tmp_path: Path):
    image = tmp_path / "card.img"
    _hfs_image(image)

    files = inventory_braw_files(image)

    assert len(files) == 1
    assert files[0].id == 42
    assert files[0].path == "/clip.braw"
    assert files[0].logical_size == 9
    assert files[0].create_date == "1904-01-01T00:00:01+00:00"
    assert files[0].extents == [{"start_block": 20, "block_count": 1, "image_offset": 10240, "byte_count": 512}]


def test_inventory_rejects_extent_overflow(tmp_path: Path):
    image = tmp_path / "card.img"
    _hfs_image(image, overflow=True)

    with pytest.raises(ValueError, match="extents overflow parsing not implemented"):
        inventory_braw_files(image)


def test_extract_writes_selected_file_without_overwriting(tmp_path: Path):
    image = tmp_path / "card.img"
    _hfs_image(image)
    target = inventory_braw_files(image)[0]
    out_dir = tmp_path / "out"

    output = extract_braw_file(image, target, out_dir)

    assert output == out_dir / "clip.braw"
    assert output.read_bytes() == b"BRAW DATA"
    with pytest.raises(ValueError, match="already exists"):
        extract_braw_file(image, target, out_dir)


@pytest.mark.parametrize(
    "path",
    [
        r"C:/escape.braw",
        r"C:folder/escape.braw",
        r"/folder/clip.braw:payload",
        r"/bad<folder/clip.braw",
        r"/folder/clip?.braw",
        r"/CON.braw/clip.braw",
        r"/folder/CON.braw",
        r"C:escape.braw",
        r"C:\\clips\\escape.braw",
        r"\\escape.braw",
        "../escape.braw",
    ],
)
def test_extract_rejects_host_path_syntax_in_catalog_name(tmp_path: Path, path: str):
    image = tmp_path / "card.img"
    image.write_bytes(b"BRAW DATA")
    target = HfsBrawFile(path, 9, None, None, [{"image_offset": 0, "byte_count": 9}], 42)

    with pytest.raises(ValueError, match="invalid HFS\\+ file path"):
        extract_braw_file(image, target, tmp_path / "out")


def test_extract_rejects_source_path_conflict(tmp_path: Path):
    image = tmp_path / "card.img"
    image.write_bytes(b"BRAW DATA")
    target = HfsBrawFile("/card.img", 9, None, None, [{"image_offset": 0, "byte_count": 9}], 42)

    with pytest.raises(ValueError, match="same as source"):
        extract_braw_file(image, target, tmp_path)


def test_extract_removes_partial_output_after_short_source_read(tmp_path: Path):
    image = tmp_path / "card.img"
    image.write_bytes(b"BRAW")
    target = HfsBrawFile("/clip.braw", 8, None, None, [{"image_offset": 0, "byte_count": 8}], 42)
    output = tmp_path / "out" / "clip.braw"

    with pytest.raises(ValueError, match="unexpected EOF"):
        extract_braw_file(image, target, output.parent)

    assert not output.exists()


def test_cli_inventory_prints_json_and_extract_selects_by_id(tmp_path: Path, capsys):
    image = tmp_path / "card.img"
    _hfs_image(image)

    assert main(["inventory", str(image)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["braw_count"] == 1
    assert payload["braws"][0]["id"] == 42

    out_dir = tmp_path / "out"
    assert main(["extract", str(image), "--clip", "42", "--out", str(out_dir)]) == 0
    assert (out_dir / "clip.braw").read_bytes() == b"BRAW DATA"


def test_cli_extract_rejects_ambiguous_basenames(tmp_path: Path, capsys, monkeypatch):
    files = [
        HfsBrawFile("/A/clip.braw", 9, None, None, [], 42),
        HfsBrawFile("/B/clip.braw", 9, None, None, [], 43),
    ]
    monkeypatch.setattr(cli, "inventory_braw_files", lambda _: files)
    monkeypatch.setattr(cli, "extract_braw_file", lambda *_: pytest.fail("ambiguous file was extracted"))

    assert main(["extract", str(tmp_path / "card.img"), "--clip", "clip.braw", "--out", str(tmp_path / "out")]) == 1
    assert "ambiguous BRAW clip name" in capsys.readouterr().err
