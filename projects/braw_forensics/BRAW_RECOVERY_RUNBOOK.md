# BRAW Recovery Runbook

## Core Rule

Never repair the card image directly. Work read-only against the `.img`, extract the target `.braw` to a separate working copy, and create every repair attempt as a new candidate file.

A BRAW recovery is considered promising only when physical frame payloads are found after the indexed end of the visible clip. Do not invent missing frames.

## Proven C007 Pattern

Case: `F004_02200341_C007.braw`

Symptoms:

- Player showed the clip ending early.
- User reported about `4-5 s` missing.
- Initial video-only repair exposed a longer slider but playback paused at the old timecode.

Confirmed cause:

- The media payload contained `125` extra BRAW video frames after the visible/indexed end.
- At `25 fps`, `125` frames equals exactly `5.00 s`.
- The container was partially finalized: video/audio/metadata payloads existed, but `moov` tables and edit lists still described the old shorter duration.

Successful candidate:

- `F004_02200341_C007_repaired_full_125f_v6.braw`

Key v6 fixes:

- Extend video track sample tables:
  - `stsz`: add hidden frame sizes read from each frame's own BRAW payload-size field.
  - `co64`: add hidden frame offsets.
  - `stts`, `tkhd`, `mdhd`: update duration/count to the new frame total.
- Extend audio track:
  - add hidden audio chunk offsets found in large inter-frame service gaps.
  - update audio duration/sample count.
- Extend metadata/timecode-like tracks:
  - add hidden service chunk offsets found in medium inter-frame service gaps.
  - update sample count/duration.
- Patch `elst` edit lists. This was essential: old `elst` values can make Blackmagic RAW Player pause at the old end even when `stsz/co64` are extended.
- Preserve post-`moov` padding/footer from the original file.

## Read-only Analysis Steps

1. Identify BRAW files inside the card image using the HFS+/filesystem parser.
2. Extract the target BRAW file to a working folder. Do not write to the `.img`.
3. Parse top-level BMFF/BRAW layout:
   - `mdat` offset/size
   - `moov` offset/size
   - tracks and sample tables
4. For the visible end:
   - read video `co64` offsets and `stsz` sizes
   - compute last indexed video frame end: `last_offset + last_size`
5. Scan between `last indexed video frame end` and `moov` for BRAW frame signatures:
   - known frame pattern starts with `bmdf` and contains `braw` at offset `+256`
   - frame size is `payload_size_at_offset_260 + 256`
6. Compare found hidden frame count to the claimed missing duration:
   - for 25 fps, `missing_seconds * 25 = expected hidden frames`
7. Inspect inter-frame gaps:
   - small gaps are normal padding/interleave
   - medium gaps often indicate metadata/timecode-like chunks
   - large gaps about once per second often indicate audio chunks
8. Compare those gap patterns against the finalized part of the same clip or a good reference BRAW.

## Repair Candidate Steps

Create a new candidate file:

1. Copy original `mdat` bytes unchanged.
2. Rebuild `moov` with patched box sizes.
3. Patch standard tables:
   - `mvhd`
   - `trak/tkhd`
   - `mdia/mdhd`
   - `edts/elst`
   - `stbl/stts`
   - `stbl/stsz`
   - `stbl/co64`
4. Preserve original post-`moov` trailing bytes/padding.
5. Never overwrite the extracted original BRAW.
6. Never write back into the card image.

## Verification Checklist

Before calling a candidate successful:

- Re-parse the candidate with the independent table dumper.
- Confirm old duration/count values are gone from `moov` when they should be replaced.
- Confirm expected counts:
  - video frames = original + hidden frames
  - audio chunks extended if hidden audio chunks exist
  - metadata/timecode-like chunks extended if hidden service chunks exist
  - `elst` durations match new intended duration
- Open in Blackmagic RAW Player or DaVinci Resolve.
- Verify playback reaches the recovered end, not just that the slider is longer.
- Ask the user to visually confirm the last seconds.

## Probability Heuristic

High confidence recovery:

- consecutive hidden BRAW frame signatures are present immediately after indexed end
- hidden frame count matches missing duration
- frame sizes are internally readable and non-overlapping
- service gaps continue the same pattern as the finalized section

Medium confidence recovery:

- video frames are present, but audio/metadata chunks are incomplete or ambiguous
- video-only repair may work, but player may pause or lose timecode

Low confidence recovery:

- no hidden frame signatures after indexed end
- tail is all zeroes or belongs to the next file
- missing duration estimate does not match physical data

## When To Stop Manual Repair

Stop manual patching and recommend a BRAW-aware repair tool/service when:

- BRAW Player still stops after standard BMFF tables and `elst` are consistent
- hidden frames exist but proprietary BRAW metadata/indexes cannot be inferred safely
- audio/timecode must be recovered perfectly for delivery
- multiple candidates create inconsistent player behavior

Recommended next escalation for hard cases: Aero Quartet / Treasured or another BRAW-aware repair workflow, using copies only.

## Future Software Plan

Build a dedicated recovery tool around this successful workflow:

- card image read-only scanner
- HFS+ BRAW inventory/extractor
- BRAW/BMFF table parser
- hidden-frame scanner
- service-gap classifier
- reference-clip comparator
- candidate builder with versioned outputs
- validation/report generator
- no-write-to-image safety guard
