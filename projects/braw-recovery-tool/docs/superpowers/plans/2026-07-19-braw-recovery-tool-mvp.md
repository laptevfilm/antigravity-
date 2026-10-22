# BRAW Recovery Tool MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Python CLI that analyzes and repairs partially finalized `.braw` files using the proven C007/C009 workflow.

**Architecture:** Create a reusable `brawrec` Python package with small modules for BMFF parsing, BRAW table summaries, hidden-frame scanning, repair candidate building, and reports. The CLI remains a thin layer over the core so a Windows GUI can later call the same functions.

**Tech Stack:** Python 3.12 standard library, `argparse`, `dataclasses`, `json`, `pathlib`, `pytest`.

## Global Constraints

- Source `.img` and `.braw` files are always opened read-only.
- Never overwrite the extracted source `.braw`.
- Every repair attempt writes a new candidate path.
- Refuse output paths that resolve to the same path as the source.
- Do not add frames unless each frame is physically found, size-validated, and non-overlapping.
- Preserve original `mdat` media bytes and post-`moov` trailing bytes.
- Report low-confidence cases instead of forcing a repair.
- MVP is Python CLI only; GUI comes after CLI stability.

---

## File Structure

- Create: `pyproject.toml` — project metadata, CLI entry point, pytest config.
- Create: `README.md` — short local usage and safety notes.
- Create: `src/brawrec/__init__.py` — package marker and version.
- Create: `src/brawrec/cli.py` — `inventory`, `extract`, `analyze`, `repair`, `verify` commands.
- Create: `src/brawrec/bmff/boxes.py` — endian helpers and BMFF box traversal.
- Create: `src/brawrec/braw/tables.py` — normalized `BrawLayout` and track table parsing.
- Create: `src/brawrec/recovery/scan.py` — hidden BRAW frame scan and validation.
- Create: `src/brawrec/recovery/service_gaps.py` — service chunk heuristics.
- Create: `src/brawrec/recovery/repair.py` — patch planning and candidate writing.
- Create: `src/brawrec/reports.py` — JSON and Markdown report writing.
- Create: `src/brawrec/filesystem/hfs.py` — HFS+ inventory/extract port from existing script.
- Create: `tests/fixtures.py` — small synthetic BMFF/BRAW fixture builders.
- Create tests under `tests/` matching each module.

---

### Task 1: Project Skeleton and CLI Shell

**Files:**
- Create: `D:\AI\braw-recovery-tool\pyproject.toml`
- Create: `D:\AI\braw-recovery-tool\README.md`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\__init__.py`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\cli.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_cli.py`

**Interfaces:**
- Produces: `brawrec.cli.main(argv: list[str] | None = None) -> int`
- Produces CLI commands: `inventory`, `extract`, `analyze`, `repair`, `verify`

- [ ] **Step 1: Write the failing CLI test**

```python
from brawrec.cli import main


def test_cli_help_returns_success(capsys):
    rc = main(["--help"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "inventory" in out
    assert "repair" in out


def test_cli_analyze_requires_source(capsys):
    rc = main(["analyze"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "source" in err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL because `brawrec.cli` does not exist.

- [ ] **Step 3: Add project metadata**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "braw-recovery-tool"
version = "0.1.0"
description = "Forensic-safe Blackmagic RAW recovery CLI"
requires-python = ">=3.12"
dependencies = []

[project.scripts]
brawrec = "brawrec.cli:console_main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 4: Add minimal package and CLI**

```python
# src/brawrec/__init__.py
__version__ = "0.1.0"
```

```python
# src/brawrec/cli.py
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brawrec")
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory")
    inventory.add_argument("card_image")

    extract = sub.add_parser("extract")
    extract.add_argument("card_image")
    extract.add_argument("--clip", required=True)
    extract.add_argument("--out", required=True)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("source")
    analyze.add_argument("--out", default=".")

    repair = sub.add_parser("repair")
    repair.add_argument("source")
    repair.add_argument("--out", required=True)
    repair.add_argument("--report", default=".")

    verify = sub.add_parser("verify")
    verify.add_argument("candidate")
    verify.add_argument("--out", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0


def console_main() -> None:
    raise SystemExit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md src/brawrec/__init__.py src/brawrec/cli.py tests/test_cli.py
git commit -m "feat: add CLI project skeleton"
```

---

### Task 2: BMFF Box Parser

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\bmff\__init__.py`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\bmff\boxes.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_boxes.py`

**Interfaces:**
- Produces: `u32(data: bytes | bytearray, offset: int) -> int`
- Produces: `u64(data: bytes | bytearray, offset: int) -> int`
- Produces: `p32(value: int) -> bytes`
- Produces: `p64(value: int) -> bytes`
- Produces: `Box(offset: int, size: int, header_size: int, type: str, path: str)`
- Produces: `iter_boxes(data: bytes, start: int, end: int) -> Iterator[Box]`
- Produces: `walk_boxes(data: bytes, start: int, end: int, path: str = "") -> Iterator[Box]`

- [ ] **Step 1: Write failing tests**

```python
import pytest

from brawrec.bmff.boxes import iter_boxes, p32, p64, u32, u64, walk_boxes


def box(kind: bytes, body: bytes) -> bytes:
    return p32(8 + len(body)) + kind + body


def test_endian_helpers_round_trip():
    data = p32(25) + p64(123456789)
    assert u32(data, 0) == 25
    assert u64(data, 4) == 123456789


def test_iter_boxes_reads_standard_and_large_sizes():
    regular = box(b"free", b"abc")
    large = p32(1) + b"mdat" + p64(20) + b"xxxx"
    parsed = list(iter_boxes(regular + large, 0, len(regular + large)))
    assert [(b.type, b.size, b.header_size) for b in parsed] == [
        ("free", 11, 8),
        ("mdat", 20, 16),
    ]


def test_walk_boxes_descends_into_moov_trak():
    trak = box(b"trak", box(b"tkhd", b"\0" * 24))
    moov = box(b"moov", trak)
    paths = [b.path for b in walk_boxes(moov, 0, len(moov))]
    assert paths == ["moov", "moov/trak", "moov/trak/tkhd"]


def test_iter_boxes_rejects_invalid_size():
    with pytest.raises(ValueError, match="invalid box"):
        list(iter_boxes(p32(4) + b"free", 0, 8))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_boxes.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement parser**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator
import struct


CONTAINERS = {"moov", "trak", "mdia", "minf", "stbl", "edts", "tref", "dinf", "udta", "meta"}


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def u64(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">Q", data, offset)[0]


def p32(value: int) -> bytes:
    return struct.pack(">I", value)


def p64(value: int) -> bytes:
    return struct.pack(">Q", value)


@dataclass(frozen=True)
class Box:
    offset: int
    size: int
    header_size: int
    type: str
    path: str

    @property
    def body_offset(self) -> int:
        return self.offset + self.header_size

    @property
    def end_offset(self) -> int:
        return self.offset + self.size


def iter_boxes(data: bytes, start: int, end: int) -> Iterator[Box]:
    pos = start
    while pos + 8 <= end:
        size = u32(data, pos)
        kind = data[pos + 4:pos + 8].decode("latin-1", "replace")
        header_size = 8
        if size == 1:
            if pos + 16 > end:
                raise ValueError(f"invalid box {kind!r} at {pos}: missing 64-bit size")
            size = u64(data, pos + 8)
            header_size = 16
        elif size == 0:
            size = end - pos
        if size < header_size or pos + size > end:
            raise ValueError(f"invalid box {kind!r} at {pos}, size {size}")
        yield Box(pos, size, header_size, kind, kind)
        pos += size
    if pos != end:
        raise ValueError(f"box parse stopped at {pos}, expected {end}")


def walk_boxes(data: bytes, start: int, end: int, path: str = "") -> Iterator[Box]:
    for box in iter_boxes(data, start, end):
        cur_path = f"{path}/{box.type}" if path else box.type
        current = Box(box.offset, box.size, box.header_size, box.type, cur_path)
        yield current
        child_start = box.body_offset + (4 if box.type == "meta" else 0)
        if box.type in CONTAINERS and child_start < box.end_offset:
            yield from walk_boxes(data, child_start, box.end_offset, cur_path)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_boxes.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/brawrec/bmff/__init__.py src/brawrec/bmff/boxes.py tests/test_boxes.py
git commit -m "feat: add BMFF box parser"
```

---

### Task 3: BRAW Layout and Track Table Parser

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\braw\__init__.py`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\braw\tables.py`
- Create: `D:\AI\braw-recovery-tool\tests\fixtures.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_tables.py`

**Interfaces:**
- Consumes: `brawrec.bmff.boxes`
- Produces: `TrackSummary(track_id: int, sample_type: str | None, timescale: int | None, tkhd_duration: int | None, mdhd_duration: int | None, stts: list[tuple[int, int]], sizes: list[int], offsets: list[int])`
- Produces: `BrawLayout(path: Path, mdat_size: int, moov_offset: int, moov_size: int, tracks: dict[int, TrackSummary], trailing_size: int)`
- Produces: `parse_braw_layout(path: Path) -> BrawLayout`
- Produces: `find_video_track(layout: BrawLayout) -> TrackSummary`
- Produces: `visible_indexed_video_end(layout: BrawLayout) -> int`

- [ ] **Step 1: Write fixture builder**

```python
from brawrec.bmff.boxes import p32, p64


def box(kind: bytes, body: bytes) -> bytes:
    return p32(8 + len(body)) + kind + body


def fullbox_body(version_flags: bytes = b"\0\0\0\0") -> bytes:
    return version_flags


def tkhd(track_id: int, duration: int) -> bytes:
    body = bytearray(fullbox_body())
    body.extend(b"\0" * 8)
    body.extend(p32(track_id))
    body.extend(b"\0" * 4)
    body.extend(p32(duration))
    body.extend(b"\0" * 60)
    return box(b"tkhd", bytes(body))


def mdhd(timescale: int, duration: int) -> bytes:
    body = bytearray(fullbox_body())
    body.extend(b"\0" * 8)
    body.extend(p32(timescale))
    body.extend(p32(duration))
    body.extend(b"\0" * 4)
    return box(b"mdhd", bytes(body))


def stsd(sample_type: bytes) -> bytes:
    body = bytearray(fullbox_body())
    body.extend(p32(1))
    body.extend(p32(16))
    body.extend(sample_type)
    body.extend(b"\0" * 8)
    return box(b"stsd", bytes(body))


def stts(count: int, delta: int) -> bytes:
    return box(b"stts", fullbox_body() + p32(1) + p32(count) + p32(delta))


def stsz(sizes: list[int]) -> bytes:
    body = bytearray(fullbox_body() + p32(0) + p32(len(sizes)))
    for size in sizes:
        body.extend(p32(size))
    return box(b"stsz", bytes(body))


def co64(offsets: list[int]) -> bytes:
    body = bytearray(fullbox_body() + p32(len(offsets)))
    for offset in offsets:
        body.extend(p64(offset))
    return box(b"co64", bytes(body))


def trak(track_id: int, sample_type: bytes, sizes: list[int], offsets: list[int], timescale: int = 25) -> bytes:
    sample_count = len(sizes)
    stbl = box(b"stbl", stsd(sample_type) + stts(sample_count, 1) + stsz(sizes) + co64(offsets))
    minf = box(b"minf", stbl)
    mdia = box(b"mdia", mdhd(timescale, sample_count) + minf)
    return box(b"trak", tkhd(track_id, sample_count) + mdia)


def synthetic_braw(sizes: list[int], offsets: list[int], mdat_size: int) -> bytes:
    moov = box(b"moov", trak(1, b"braw", sizes, offsets))
    return p32(1) + b"mdat" + p64(mdat_size) + b"\0" * (mdat_size - 16) + moov + b"tail"
```

- [ ] **Step 2: Write failing parser tests**

```python
from pathlib import Path

from brawrec.braw.tables import find_video_track, parse_braw_layout, visible_indexed_video_end
from tests.fixtures import synthetic_braw


def test_parse_braw_layout_reads_mdat_moov_and_track_tables(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100, 120], [256, 512], 2048))

    layout = parse_braw_layout(source)

    assert layout.mdat_size == 2048
    assert layout.moov_offset == 2048
    assert layout.trailing_size == 4
    track = layout.tracks[1]
    assert track.sample_type == "braw"
    assert track.sizes == [100, 120]
    assert track.offsets == [256, 512]
    assert track.stts == [(2, 1)]


def test_visible_indexed_video_end_uses_last_offset_plus_size(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100, 120], [256, 512], 2048))

    layout = parse_braw_layout(source)

    assert find_video_track(layout).track_id == 1
    assert visible_indexed_video_end(layout) == 632
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_tables.py -v`

Expected: FAIL because `brawrec.braw.tables` does not exist.

- [ ] **Step 4: Implement table parser**

Implement `tables.py` by porting the table parsing from `D:\AI\braw_forensics\dump_braw_tables.py`, but return dataclasses instead of printing JSON. Keep parsing read-only: use `Path.open("rb")`, `seek`, and `read`.

Minimum implementation details:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brawrec.bmff.boxes import Box, iter_boxes, u32, u64, walk_boxes


@dataclass(frozen=True)
class TrackSummary:
    track_id: int
    sample_type: str | None
    timescale: int | None
    tkhd_duration: int | None
    mdhd_duration: int | None
    stts: list[tuple[int, int]]
    sizes: list[int]
    offsets: list[int]


@dataclass(frozen=True)
class BrawLayout:
    path: Path
    mdat_size: int
    moov_offset: int
    moov_size: int
    tracks: dict[int, TrackSummary]
    trailing_size: int
    moov: bytes


def parse_braw_layout(path: Path) -> BrawLayout:
    with path.open("rb") as f:
        head = f.read(16)
        if len(head) < 16 or head[4:8] != b"mdat":
            raise ValueError("expected mdat-first BRAW")
        mdat_size = u64(head, 8) if u32(head, 0) == 1 else u32(head, 0)
        f.seek(mdat_size)
        moov_head = f.read(8)
        if len(moov_head) < 8 or moov_head[4:8] != b"moov":
            raise ValueError("moov not found at mdat end")
        moov_size = u32(moov_head, 0)
        f.seek(mdat_size)
        moov = f.read(moov_size)
        f.seek(0, 2)
        file_size = f.tell()
    return BrawLayout(path, mdat_size, mdat_size, moov_size, _parse_tracks(moov), file_size - mdat_size - moov_size, moov)
```

Also implement `_parse_tracks`, `_parse_stsz`, `_parse_table`, `find_video_track`, and `visible_indexed_video_end` with the signatures above.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_tables.py tests/test_boxes.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/brawrec/braw/__init__.py src/brawrec/braw/tables.py tests/fixtures.py tests/test_tables.py
git commit -m "feat: parse BRAW track tables"
```

---

### Task 4: Hidden Frame Scanner

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\recovery\__init__.py`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\recovery\scan.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_scan.py`

**Interfaces:**
- Consumes: `BrawLayout`
- Produces: `HiddenFrame(offset: int, size: int)`
- Produces: `scan_hidden_video(layout: BrawLayout, start: int | None = None) -> list[HiddenFrame]`

- [ ] **Step 1: Write failing scanner tests**

```python
from pathlib import Path

import pytest

from brawrec.braw.tables import parse_braw_layout
from brawrec.recovery.scan import FRAME_PATTERN, scan_hidden_video
from tests.fixtures import synthetic_braw


def frame(payload_size: int) -> bytes:
    data = bytearray(256 + payload_size)
    data[:len(FRAME_PATTERN)] = FRAME_PATTERN
    data[256:260] = b"braw"
    data[260:264] = payload_size.to_bytes(4, "big")
    return bytes(data)


def test_scan_hidden_video_finds_valid_non_overlapping_frames(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    hidden = frame(300)
    payload[512:512 + len(hidden)] = hidden
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)
    frames = scan_hidden_video(layout, start=512)

    assert [(f.offset, f.size) for f in frames] == [(512, 556)]


def test_scan_hidden_video_rejects_overlap(tmp_path: Path):
    source = tmp_path / "clip.braw"
    payload = bytearray(synthetic_braw([100], [256], 2048))
    first = frame(800)
    second = frame(100)
    payload[512:512 + len(first)] = first
    payload[700:700 + len(second)] = second
    source.write_bytes(bytes(payload))

    layout = parse_braw_layout(source)
    with pytest.raises(ValueError, match="overlaps"):
        scan_hidden_video(layout, start=512)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scan.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement scanner**

Port `scan_hidden_video` from `repair_c007_full_index.py` and `repair_c009_full_index.py`, but return `HiddenFrame` dataclasses. Scan chunks of `64 * 1024 * 1024` bytes and keep overlap of `len(FRAME_PATTERN) - 1`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_scan.py tests/test_tables.py tests/test_boxes.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/brawrec/recovery/__init__.py src/brawrec/recovery/scan.py tests/test_scan.py
git commit -m "feat: scan hidden BRAW frames"
```

---

### Task 5: Service Gap Classifier

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\recovery\service_gaps.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_service_gaps.py`

**Interfaces:**
- Consumes: `HiddenFrame`
- Produces: `ServiceGap(kind: str, start: int, end: int, first_nonzero: int | None, aligned_offset: int | None)`
- Produces: `classify_service_gaps(path: Path, frames: list[HiddenFrame], moov_offset: int) -> list[ServiceGap]`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path

from brawrec.recovery.scan import HiddenFrame
from brawrec.recovery.service_gaps import classify_service_gaps


def test_classify_medium_and_large_nonzero_gaps(tmp_path: Path):
    path = tmp_path / "clip.braw"
    data = bytearray(2_000_000)
    data[600_123] = 1
    data[1_200_123] = 1
    path.write_bytes(bytes(data))

    frames = [
        HiddenFrame(offset=100_000, size=100_000),
        HiddenFrame(offset=650_000, size=100_000),
        HiddenFrame(offset=1_550_000, size=100_000),
    ]

    gaps = classify_service_gaps(path, frames, moov_offset=1_900_000)

    assert [g.kind for g in gaps[:2]] == ["large", "large"]
    assert gaps[0].aligned_offset == 600_064
    assert gaps[1].aligned_offset == 1_200_128 - 128
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_service_gaps.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement classifier**

Implement thresholds from the runbook:

- `gap < 30_000`: `small`
- `30_000 <= gap < 80_000`: `medium`
- `250_000 <= gap < 400_000`: `large`
- otherwise: `unknown`

Use `floor_align(value, 256)` for the first nonzero byte. Return all gaps, not only accepted service chunks, so reports can explain decisions.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_service_gaps.py tests/test_scan.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/brawrec/recovery/service_gaps.py tests/test_service_gaps.py
git commit -m "feat: classify hidden service gaps"
```

---

### Task 6: Candidate Repair Builder

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\recovery\repair.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_repair.py`

**Interfaces:**
- Consumes: `BrawLayout`, `TrackSummary`, `HiddenFrame`
- Produces: `RepairPlan(source: Path, output: Path, hidden_frames: list[HiddenFrame], video_track_id: int, final_video_frames: int, confidence: str)`
- Produces: `build_repair_plan(layout: BrawLayout, output: Path, hidden_frames: list[HiddenFrame]) -> RepairPlan`
- Produces: `write_candidate(plan: RepairPlan) -> None`

- [ ] **Step 1: Write failing safety and planning tests**

```python
from pathlib import Path

import pytest

from brawrec.braw.tables import parse_braw_layout
from brawrec.recovery.repair import build_repair_plan
from brawrec.recovery.scan import HiddenFrame
from tests.fixtures import synthetic_braw


def test_build_repair_plan_rejects_source_output_conflict(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    layout = parse_braw_layout(source)

    with pytest.raises(ValueError, match="same as source"):
        build_repair_plan(layout, source, [HiddenFrame(offset=512, size=556)])


def test_build_repair_plan_counts_final_video_frames(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100, 120], [256, 512], 2048))
    layout = parse_braw_layout(source)
    output = tmp_path / "candidate.braw"

    plan = build_repair_plan(layout, output, [HiddenFrame(offset=768, size=556)])

    assert plan.final_video_frames == 3
    assert plan.video_track_id == 1
    assert plan.confidence == "high"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_repair.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement minimal repair plan**

Implement `build_repair_plan` first. Do not write bytes yet. It must:

- resolve source and output paths;
- reject same path;
- reject empty `hidden_frames` with `ValueError("no hidden frames to repair")`;
- compute `final_video_frames = len(video_track.sizes) + len(hidden_frames)`;
- set `confidence = "high"` when all hidden frames are present and nonempty.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_repair.py -v`

Expected: PASS.

- [ ] **Step 5: Add candidate writing tests**

```python
from brawrec.recovery.repair import write_candidate


def test_write_candidate_preserves_source_and_writes_output(tmp_path: Path):
    source = tmp_path / "clip.braw"
    original = synthetic_braw([100], [256], 2048)
    source.write_bytes(original)
    layout = parse_braw_layout(source)
    output = tmp_path / "candidate.braw"
    plan = build_repair_plan(layout, output, [HiddenFrame(offset=512, size=556)])

    write_candidate(plan)

    assert source.read_bytes() == original
    assert output.exists()
    assert output.stat().st_size >= source.stat().st_size
```

- [ ] **Step 6: Implement candidate writer**

Generalize the rebuild logic from `repair_c007_full_index.py` and `repair_c009_full_index.py`:

- patch video `stsz` by appending hidden frame sizes;
- patch video `co64` by appending hidden frame offsets;
- patch one-entry `stts` count to final video frame count;
- patch `tkhd`, `mdhd`, and `elst` durations for the video track;
- copy source bytes to the output with rebuilt `moov`;
- preserve source file bytes unchanged.

Keep audio/metadata patching behind explicit data structures so Task 8 can extend it without changing the public interface.

- [ ] **Step 7: Run tests**

Run: `python -m pytest tests/test_repair.py tests/test_tables.py tests/test_scan.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/brawrec/recovery/repair.py tests/test_repair.py
git commit -m "feat: build BRAW repair candidates"
```

---

### Task 7: Reports and CLI Integration

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\reports.py`
- Modify: `D:\AI\braw-recovery-tool\src\brawrec\cli.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_reports.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_cli_integration.py`

**Interfaces:**
- Produces: `write_json_report(path: Path, payload: dict) -> None`
- Produces: `write_markdown_report(path: Path, title: str, payload: dict) -> None`
- CLI `analyze` writes `analysis.json` and `analysis.md`
- CLI `repair` writes candidate plus `repair.json` and `repair.md`
- CLI `verify` writes `verify.json` and `verify.md`

- [ ] **Step 1: Write failing report tests**

```python
import json
from pathlib import Path

from brawrec.reports import write_json_report, write_markdown_report


def test_write_json_report_creates_parent_and_pretty_json(tmp_path: Path):
    out = tmp_path / "reports" / "analysis.json"
    write_json_report(out, {"hidden_frames": 24})
    assert json.loads(out.read_text(encoding="utf-8")) == {"hidden_frames": 24}
    assert "\n  " in out.read_text(encoding="utf-8")


def test_write_markdown_report_contains_title_and_values(tmp_path: Path):
    out = tmp_path / "analysis.md"
    write_markdown_report(out, "Analysis", {"hidden_frames": 24})
    text = out.read_text(encoding="utf-8")
    assert "# Analysis" in text
    assert "hidden_frames" in text
    assert "24" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_reports.py -v`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement reports**

Use only `json.dumps(..., ensure_ascii=False, indent=2)` and simple Markdown key/value sections.

- [ ] **Step 4: Write CLI integration tests**

```python
from pathlib import Path

from brawrec.cli import main
from tests.fixtures import synthetic_braw


def test_analyze_command_writes_reports(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(synthetic_braw([100], [256], 2048))
    out = tmp_path / "reports"

    rc = main(["analyze", str(source), "--out", str(out)])

    assert rc == 0
    assert (out / "analysis.json").exists()
    assert (out / "analysis.md").exists()
```

- [ ] **Step 5: Wire CLI commands**

Implement command dispatch:

- `analyze`: parse layout, compute visible end, scan hidden frames, classify gaps, write reports.
- `repair`: run analyze path, build repair plan, write candidate, write reports.
- `verify`: parse candidate layout and write track counts/durations.
- `inventory` and `extract`: call HFS functions added in Task 9; until Task 9 exists, return `2` with message `"inventory/extract not available yet"` only if this task is executed before Task 9.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_reports.py tests/test_cli_integration.py tests/test_cli.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/brawrec/reports.py src/brawrec/cli.py tests/test_reports.py tests/test_cli_integration.py
git commit -m "feat: add reports and CLI workflows"
```

---

### Task 8: Audio and Metadata Service Chunk Extension

**Files:**
- Modify: `D:\AI\braw-recovery-tool\src\brawrec\recovery\repair.py`
- Modify: `D:\AI\braw-recovery-tool\src\brawrec\recovery\service_gaps.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_repair_service_tracks.py`

**Interfaces:**
- Consumes: `ServiceGap`
- Produces: `ServicePatch(track_id: int, offsets: list[int], added_samples: int)`
- Produces: optional `service_patches: dict[int, ServicePatch]` on `RepairPlan`

- [ ] **Step 1: Write tests using C007/C009-derived expectations**

```python
from brawrec.recovery.repair import ServicePatch


def test_service_patch_records_offsets_and_samples():
    patch = ServicePatch(track_id=5, offsets=[13_303_263_232], added_samples=48_000)
    assert patch.track_id == 5
    assert patch.offsets == [13_303_263_232]
    assert patch.added_samples == 48_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_repair_service_tracks.py -v`

Expected: FAIL because `ServicePatch` does not exist.

- [ ] **Step 3: Add service patch model and patch application**

Implement service patches so repair can extend non-video `co64`, `stsz` fixed-count tracks, `stts`, `tkhd`, `mdhd`, and `elst` when a caller supplies physically found service offsets.

Use C009 as the first generalized target:

- one metadata/timecode-like pair adds `1024` samples to each metadata track;
- one audio chunk adds `48_000` samples to audio at 25 fps cases observed so far.

Keep these values explicit in the report, not hidden magic.

- [ ] **Step 4: Run full tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/brawrec/recovery/repair.py src/brawrec/recovery/service_gaps.py tests/test_repair_service_tracks.py
git commit -m "feat: extend service tracks during repair"
```

---

### Task 9: HFS+ Inventory and Extraction

**Files:**
- Create: `D:\AI\braw-recovery-tool\src\brawrec\filesystem\__init__.py`
- Create: `D:\AI\braw-recovery-tool\src\brawrec\filesystem\hfs.py`
- Modify: `D:\AI\braw-recovery-tool\src\brawrec\cli.py`
- Test: `D:\AI\braw-recovery-tool\tests\test_hfs.py`

**Interfaces:**
- Produces: `HfsBrawFile(path: str, logical_size: int, create_date: str | None, content_mod_date: str | None, extents: list[dict])`
- Produces: `inventory_braw_files(image_path: Path, part_offset: int = 0) -> list[HfsBrawFile]`
- Produces: `extract_braw_file(image_path: Path, target: HfsBrawFile, out_dir: Path) -> Path`

- [ ] **Step 1: Port parser with smoke tests**

Port the safe parts of `D:\AI\braw_forensics\analyze_hfs_braw.py` and `D:\AI\braw_forensics\extract_hfs_file.py`. Keep the same limitation explicit: if a file needs extents overflow parsing beyond inline extents, raise `ValueError("extents overflow parsing not implemented")`.

- [ ] **Step 2: Wire CLI**

`inventory <card-image>` prints JSON to stdout and writes no files unless `--out` is added in a future task.

`extract <card-image> --clip <name-or-id> --out <folder>` extracts one file and refuses to overwrite an existing output path.

- [ ] **Step 3: Run available tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 4: Run real inventory smoke test when `E:\C022.img` is available**

Run: `brawrec inventory E:\C022.img`

Expected: JSON includes `C022_07042240_C009.braw`.

- [ ] **Step 5: Commit**

```bash
git add src/brawrec/filesystem/__init__.py src/brawrec/filesystem/hfs.py src/brawrec/cli.py tests/test_hfs.py
git commit -m "feat: add HFS BRAW inventory and extraction"
```

---

### Task 10: End-to-End Regression on C007 and C009

**Files:**
- Create: `D:\AI\braw-recovery-tool\tests\test_regression_reports.py`
- Modify: `D:\AI\braw-recovery-tool\README.md`

**Interfaces:**
- Consumes CLI commands from earlier tasks.
- Produces documented verification commands and expected counts.

- [ ] **Step 1: Add regression documentation**

Document these manual checks in `README.md`:

```text
brawrec analyze D:\AI\braw_forensics\F004\F004_02200341_C007.braw --out D:\AI\braw-recovery-tool\runs\C007
brawrec repair D:\AI\braw_forensics\F004\F004_02200341_C007.braw --out D:\AI\braw-recovery-tool\runs\C007\C007_candidate.braw --report D:\AI\braw-recovery-tool\runs\C007
brawrec verify D:\AI\braw-recovery-tool\runs\C007\C007_candidate.braw --out D:\AI\braw-recovery-tool\runs\C007

brawrec analyze D:\AI\braw_forensics\C022_new\C022_07042240_C009.braw --out D:\AI\braw-recovery-tool\runs\C009
brawrec repair D:\AI\braw_forensics\C022_new\C022_07042240_C009.braw --out D:\AI\braw-recovery-tool\runs\C009\C009_candidate.braw --report D:\AI\braw-recovery-tool\runs\C009
brawrec verify D:\AI\braw-recovery-tool\runs\C009\C009_candidate.braw --out D:\AI\braw-recovery-tool\runs\C009
```

Expected:

- C007: `756 -> 881` video frames, `+125` hidden frames.
- C009: `1638 -> 1662` video frames, `+24` hidden frames.

- [ ] **Step 2: Run full unit tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 3: Run C007 manual regression if source file exists**

Run the C007 commands from README.

Expected: reports show `hidden_frames: 125` and candidate video count `881`.

- [ ] **Step 4: Run C009 manual regression if source file exists**

Run the C009 commands from README.

Expected: reports show `hidden_frames: 24` and candidate video count `1662`.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_regression_reports.py
git commit -m "test: document BRAW recovery regressions"
```

---

## Self-Review

Spec coverage:

- Read-only `.braw` inspection: Tasks 3, 4, 7.
- HFS+ card image inventory/extract: Task 9.
- BRAW/BMFF parsing: Tasks 2 and 3.
- Hidden frame scanning: Task 4.
- Service-gap classification: Task 5.
- Candidate repair generation: Tasks 6 and 8.
- Independent verification and reports: Tasks 7 and 10.
- Safety guards: Tasks 6, 7, 9, 10.
- C007/C009 validation: Task 10.

Open-marker scan:

- No unfinished-work markers are intentionally present.
- Task 8 leaves proprietary inference limited to explicit observed cases.
- Task 9 explicitly scopes unsupported HFS+ extents overflow behavior.

Type consistency:

- `BrawLayout`, `TrackSummary`, `HiddenFrame`, `ServiceGap`, `RepairPlan`, and `ServicePatch` names are introduced before dependent tasks use them.
- CLI command names match the approved design.
