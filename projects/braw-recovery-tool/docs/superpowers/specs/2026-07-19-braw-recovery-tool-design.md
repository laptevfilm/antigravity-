# BRAW Recovery Tool MVP Design

## Goal

Build a local Windows-first recovery tool for partially finalized Blackmagic RAW
(`.braw`) clips, based on the proven C007 and C009 recovery workflow.

The MVP is a Python command-line tool with a clean recovery core. A Windows GUI
can be added later without rewriting the forensic logic.

## Scope

The first version handles cases where a `.braw` file contains real video frame
payloads after the old indexed end of the clip, but its `moov` tables still
describe the shorter duration.

The MVP supports:

- read-only inspection of `.braw` files;
- read-only inventory and extraction from HFS+ card images when the current
  HFS+ parser can describe the file through inline extents;
- BRAW/BMFF parsing for `mdat`, `moov`, tracks, sample sizes, offsets, timing,
  durations, and edit lists;
- hidden frame scanning using confirmed BRAW frame signatures;
- service-gap classification for hidden audio and metadata/timecode chunks;
- candidate repair file generation;
- independent table verification;
- JSON and Markdown reports.

The MVP does not promise:

- recovery when no physical hidden frames are present;
- invented or interpolated frames;
- perfect repair for proprietary BRAW metadata that cannot be inferred safely;
- direct writing to card images or source `.braw` files;
- a GUI in the first implementation milestone.

## Safety Rules

Source media is evidence.

- Open card images and source `.braw` files read-only.
- Never overwrite the extracted source `.braw`.
- Every repair attempt writes a new candidate path.
- Refuse output paths that resolve to the same path as the source.
- Do not add frames unless each frame is physically found, size-validated, and
  non-overlapping.
- Preserve original `mdat` media bytes and post-`moov` trailing bytes.
- Report low-confidence cases instead of forcing a repair.

## Architecture

The tool is split into a reusable core and a small CLI.

`brawrec/filesystem/hfs.py`

- Reads HFS+ volume metadata from a card image.
- Lists candidate `.braw` files with paths, logical sizes, dates, and extents.
- Extracts selected files to a working folder when extents are supported.

`brawrec/bmff/boxes.py`

- Provides big-endian integer helpers.
- Iterates BMFF boxes, including 64-bit sizes.
- Walks nested boxes such as `moov`, `trak`, `mdia`, `minf`, `stbl`, `edts`,
  and `meta`.

`brawrec/braw/tables.py`

- Reads track IDs and sample tables.
- Parses `stts`, `stsz`, `stco`, `co64`, `tkhd`, `mdhd`, and `elst`.
- Produces a normalized track summary used by analysis, repair, and verify.

`brawrec/recovery/scan.py`

- Computes the visible indexed video end.
- Scans from that byte to the `moov` boundary for the confirmed frame pattern:
  `00 00 01 00 bmdf 00 00 00 10 srte`.
- Validates the `braw` marker at frame offset `+256`.
- Reads the payload size at frame offset `+260` and adds `256` bytes.
- Rejects overlapping or implausible frames.

`brawrec/recovery/service_gaps.py`

- Inspects gaps between hidden video frames.
- Classifies small gaps as padding/interleave.
- Classifies medium nonzero gaps as metadata/timecode-like chunks.
- Classifies large roughly once-per-second gaps as audio chunks.
- Keeps heuristic decisions in the report.

`brawrec/recovery/repair.py`

- Builds repair patches for video, audio, metadata, and timing tracks.
- Rebuilds affected `moov` boxes and box sizes.
- Patches `mvhd`, `tkhd`, `mdhd`, `stts`, `stsz`, `co64`, and `edts/elst`.
- Writes a new candidate file from the original bytes plus rebuilt `moov`.

`brawrec/reports.py`

- Writes machine-readable JSON.
- Writes a concise Markdown report with source paths, frame counts, byte
  offsets, confidence, repair actions, and verification results.

`brawrec/cli.py`

- Exposes commands for inventory, extract, analyze, repair, and verify.

## CLI

Initial commands:

```text
brawrec inventory <card-image>
brawrec extract <card-image> --clip <name-or-id> --out <folder>
brawrec analyze <source.braw> --out <report-folder>
brawrec repair <source.braw> --out <candidate.braw> --report <report-folder>
brawrec verify <candidate.braw> --out <report-folder>
```

The repair command runs analysis first unless a compatible analysis report is
provided later.

## Data Flow

For a direct `.braw` repair:

1. Open source `.braw` read-only.
2. Parse `mdat` and `moov`.
3. Identify video track and compute indexed end.
4. Scan hidden frame region.
5. Classify service gaps.
6. Build patch plan.
7. Write a new candidate file.
8. Re-parse candidate independently.
9. Write JSON and Markdown reports.

For a card image:

1. Open image read-only.
2. Parse HFS+ inventory.
3. Extract selected `.braw` into a working folder.
4. Run the direct `.braw` flow against the extracted copy.

## Error Handling

Errors should be explicit and non-destructive:

- unsupported filesystem layout: report why extraction is unavailable;
- unsupported BRAW layout: report the first invalid or unexpected box;
- no hidden frames: produce analysis report and skip repair by default;
- ambiguous service gaps: allow video-only candidate only when requested later;
- output path conflict: abort before writing;
- verification mismatch: keep candidate, mark it failed, and explain mismatch.

## Validation Targets

The MVP must reproduce the two confirmed recoveries:

- C007: original `756` video frames, hidden `125`, final `881`, added `5.00 s`;
- C009: original `1638` video frames, hidden `24`, final `1662`, added `0.96 s`.

Verification checks:

- candidate `stsz/co64` counts match expected frame counts;
- `stts`, `tkhd`, `mdhd`, and `elst` durations match the intended duration;
- audio and metadata/timecode chunk counts extend only when physical chunks are
  found;
- source `.img` and source `.braw` remain unchanged;
- reports are written for every analyze, repair, and verify run.

## Implementation Order

1. Create Python package skeleton and CLI entry point.
2. Move shared BMFF box parsing into reusable modules.
3. Move table dumping into normalized parser and verifier.
4. Move hidden frame scanning into reusable recovery code.
5. Generalize C007/C009 repair scripts into a candidate builder.
6. Add report generation.
7. Add regression tests using existing metadata/reports and, where available,
   local sample BRAW files.
8. Run C007 and C009 end-to-end verification.

## Future GUI Direction

After the CLI is stable, add a Windows 11 GUI as a thin shell over the same
core. Candidate technologies are WinUI 3 / Windows App SDK or WPF/.NET.

The GUI should provide:

- file picker for `.img` or `.braw`;
- scan results;
- repair button;
- confidence/status display;
- report viewer;
- link to the candidate output.
