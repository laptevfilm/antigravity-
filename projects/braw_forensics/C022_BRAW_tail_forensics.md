# Read-only BRAW tail forensics: `E:\Ressque\C022.img`

Date: 2026-07-19  
Scope: determine whether the last visible `.braw` clip has physically present but unfinalized frames after the visible end. No repair was attempted. The image was not mounted or modified.

## Short conclusion

The last clip is `/C022_07042240_C009.braw`.

Evidence points to a finalized container whose visible duration is the duration recorded in `moov`, not an unclosed BRAW with recoverable frame data after the visible end.

Estimated chance assessment:

- Physical, recoverable BRAW frames after the visible end: low, about 5-10%.
- Unclosed/unfinalized container as the primary failure mode: low, about 5%.
- Camera stopped recording or did not commit later frames: high, about 80-90%.
- BRAW-aware repair may still be worth trying on a copy if the missing material is valuable, but the evidence is not strong for hidden frame payload.

The most suspicious finding is a large zero-filled region inside the last file: about 1,036,048,346 bytes before `moov`. That is not frame data; it is all zero padding/unwritten allocation.

## Commands run

```powershell
Get-Item -LiteralPath 'E:\Ressque\C022.img' | Select-Object FullName,Length,LastWriteTime
Format-Hex -LiteralPath 'E:\Ressque\C022.img' -Count 512
Format-Hex -LiteralPath 'E:\Ressque\C022.img' -Offset 4195328 -Count 512
py -3.10 D:\AI\braw_forensics\analyze_hfs_braw.py E:\Ressque\C022.img --out D:\AI\braw_forensics
py -3.10 D:\AI\braw_forensics\deep_braw_tail_scan.py D:\AI\braw_forensics\hfs_braw_inventory.json --after-mib 1024 --out D:\AI\braw_forensics\deep_tail_scan.json
py -3.10 D:\AI\braw_forensics\track_summary.py D:\AI\braw_forensics\hfs_braw_inventory.json D:\AI\braw_forensics\track_summary.json
py -3.10 D:\AI\braw_forensics\scan_after_last.py D:\AI\braw_forensics\hfs_braw_inventory.json 16 D:\AI\braw_forensics\after_last_16g.json
```

Notes:

- `ffprobe`, `mediainfo`, `exiftool`, and SleuthKit tools were not present in PATH.
- Python scripts only read `E:\Ressque\C022.img` and wrote JSON/CSV/Markdown evidence under `D:\AI\braw_forensics`.
- BRAW was not decoded. The scripts inspect HFS+ catalog records and ISO-BMFF-like box/sample tables.

## Image and filesystem

- Image path: `E:\Ressque\C022.img`
- Image size: `512,124,518,400` bytes
- MBR present.
- Main partition: starts at LBA `8192`, byte offset `4,194,304`.
- Partition type in MBR: `0xAF`.
- Volume header at `4,195,328` has `H+`, journaled HFS+ (`HFSJ`).
- HFS+ block size: `4096`.

## BRAW inventory

Found 9 `.braw` files in the HFS+ catalog.

| Clip | Logical size | Visible duration from `moov` | Video samples | First physical offset |
|---|---:|---:|---:|---:|
| `/C022_07041958_C001.braw` | 1,297,150,812 | 6.16 s | 154 | 1,749,024,768 |
| `/C022_07041959_C002.braw` | 479,461,160 | 2.84 s | 71 | 3,046,244,352 |
| `/C022_07042016_C003.braw` | 24,250,411,768 | 100.12 s | 2503 | 3,525,705,728 |
| `/C022_07042042_C004.braw` | 16,784,223,672 | 77.16 s | 1929 | 27,776,122,880 |
| `/C022_07042057_C005.braw` | 20,560,322,704 | 91.96 s | 2299 | 44,560,416,768 |
| `/C022_07042130_C006.braw` | 4,728,088,992 | 23.64 s | 591 | 65,120,763,904 |
| `/C022_07042136_C007.braw` | 12,585,596,520 | 58.84 s | 1471 | 69,849,186,304 |
| `/C022_07042146_C008.braw` | 11,912,260,592 | 50.60 s | 1265 | 82,434,850,816 |
| `/C022_07042240_C009.braw` | 15,888,248,832 | 65.52 s | 1638 | 94,347,198,464 |

## Last BRAW: offsets and structure

`/C022_07042240_C009.braw`

- File ID in HFS+ catalog: `28`
- Logical size: `15,888,248,832` bytes
- Allocated size: `15,888,248,832` bytes
- Physical extent: one contiguous extent
- Extent start block: `23,032,960`
- Extent block count: `3,878,967`
- File physical start: `94,347,198,464`
- File physical end: `110,235,447,296`

Top-level boxes:

| Relative offset | Type | Size | Status |
|---:|---|---:|---|
| 0 | `mdat` | 15,887,790,080 | valid |
| 15,887,790,080 | `moov` | 458,376 | valid |
| 15,888,248,456 | zero/padding | 376 | valid-sized trailing padding |

The `moov` begins at absolute offset `110,234,988,544`.

Container duration:

- `mvhd` timescale: `25`
- `mvhd` duration: `1638`
- Visible duration from container: `65.52 s`
- Main video track sample count: `1638`
- Main video sample payload total from `stsz`: `13,180,692,992` bytes

## Comparison with good reference BRAWs

The earlier BRAW files have the same broad structure: `mdat` followed by a valid `moov`. Their zero padding before `moov` is tiny:

| Clip | Zero bytes immediately before `moov` |
|---|---:|
| C001 | 3,072 |
| C002 | 3,840 |
| C003 | 2,305 |
| C004 | 3,073 |
| C005 | 2,049 |
| C006 | 0 |
| C007 | 3,840 |
| C008 | 1,392 |
| C009 | 1,036,048,346 |

This makes C009 abnormal, but in a specific way: it contains a large unwritten/zero region before a valid final `moov`, not a large region of unindexed BRAW frame bytes.

## Tail and nearby raw image data

Inside C009:

- Last non-zero byte before `moov`: relative offset `14,851,741,733`.
- `moov` starts at relative offset `15,887,790,080`.
- Zero-filled gap before `moov`: `1,036,048,346` bytes.

After C009 EOF:

- Scanned first `16 GiB` after file end, from absolute offset `110,235,447,296`.
- 4096 windows of 4 MiB each.
- 4075 windows were all zero.
- 21 windows had sparse non-zero bytes.
- Signature hits in those 16 GiB:
  - `mdat`: 0
  - `moov`: 0
  - `braw`: 4
  - `Blackmagic`: 2

The `braw/Blackmagic` hits after EOF were inspected around absolute offset `111,002,413,120`. The ASCII content references old file/metadata strings such as:

- `_07041958_C001.braw`
- `Blackmagic Design Raw Movi`
- `sidecar`
- `plain-text`
- `com.blackmagic-design.braw-movie`

That looks like HFS+/Finder metadata or sidecar/extended-attribute remnants, not contiguous video frame payload. No `mdat` or `moov` container boxes were found in the 16 GiB after EOF.

## Size versus missing seconds

From C009:

- Main video track sample payload: `13,180,692,992` bytes over `65.52 s`, about `201.17 MB/s` decimal.
- Last non-zero data before `moov`: about `14.85 GB`, about `226.68 MB/s` if divided by visible duration.

Rule of thumb for expected missing material:

- `1 s` missing would normally need roughly `201-227 MB`.
- `5 s` missing would need roughly `1.0-1.13 GB`.
- `10 s` missing would need roughly `2.0-2.27 GB`.

C009 has about `1.036 GB` of reserved-looking space before `moov`, which is in the range of roughly 4.6-5.1 seconds at this data rate. However, that region is zero-filled, so it is not physically present BRAW frame data.

Because the user-provided prompt did not include the exact visible duration observed in Resolve/Blackmagic RAW Player or the exact expected missing seconds, this report uses the container-visible duration from `moov` as the visible duration. If the externally visible duration differs from `65.52 s`, re-run the size estimate using the formula above.

## Interpretation

Evidence for finalized container:

- `mdat` has a coherent declared size.
- `moov` exists, is valid-sized, and contains duration/sample tables.
- C009 has `1638` video samples at 25 fps, matching `65.52 s`.
- The file allocation exactly equals logical size.

Evidence against physically present unfinalized frames:

- The abnormal region before `moov` is zero-filled, not frame-like data.
- The first 16 GiB after EOF contains no `mdat`/`moov` and no continuous high-entropy media stream.
- Sparse post-EOF string hits correspond to old metadata/sidecar-like content, not C009 frame payload.

Most likely scenario:

The camera or filesystem allocated/reserved more space, but the camera only committed/indexed the visible frames, then finalized the clip. The missing seconds, if any, were probably never written as usable BRAW frame payload.

## Safe next steps

1. Keep `E:\Ressque\C022.img` read-only and unchanged.
2. Work only on a duplicate image or extracted copy of `C022_07042240_C009.braw`.
3. If the material is valuable, submit the copy to a BRAW-aware repair service/tool such as Aero Quartet/Treasured. Provide:
   - the damaged/suspect C009,
   - one or more same-card reference BRAWs, preferably C007/C008,
   - this report and JSON evidence.
4. Do not attempt homemade BRAW decoding or manual rewriting of `moov`/sample tables unless a BRAW-aware tool first confirms recoverable frame chunks exist.
5. If exact expected missing duration is known, compare it to the rule-of-thumb byte estimate above. If the expected missing duration is more than about 5 seconds, this image has even weaker evidence for recoverability because the only C009-adjacent gap is zero-filled and the next 16 GiB lacks container media signatures.

## Evidence files created

- `D:\AI\braw_forensics\analyze_hfs_braw.py`
- `D:\AI\braw_forensics\deep_braw_tail_scan.py`
- `D:\AI\braw_forensics\track_summary.py`
- `D:\AI\braw_forensics\scan_after_last.py`
- `D:\AI\braw_forensics\hfs_braw_inventory.json`
- `D:\AI\braw_forensics\hfs_braw_inventory.csv`
- `D:\AI\braw_forensics\deep_tail_scan.json`
- `D:\AI\braw_forensics\track_summary.json`
- `D:\AI\braw_forensics\after_last_16g.json`
