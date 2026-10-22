# Minimal Windows Shell Design

## Goal

Build a small Windows desktop shell for the existing BRAW recovery engine. The shell should make the current MVP usable without typing commands while preserving the forensic safety rules already implemented by the CLI.

## Scope

The first shell is a Tkinter-based desktop app included in the repository and packaged as `BRAW Recovery.exe` in the same implementation stage when PyInstaller is available.

It supports:

- Selecting one source `.braw` file.
- Selecting an output folder.
- Running analyze, repair, and verify actions.
- Showing a readable status log.
- Showing the recovered candidate path after repair.

It does not support:

- Batch recovery.
- Manual service-track patch editing.
- Timeline preview or media playback.
- Direct write-back into the source file.

## User Experience

The main window is a compact work panel:

- Source file picker.
- Output folder picker, defaulting to `runs/<source-stem>` under the project folder.
- Candidate path preview, defaulting to `<source-stem>_candidate.braw`.
- Buttons for `Analyze`, `Recover`, and `Verify`.
- A log/status area with clear success or refusal messages.

The app should avoid technical jargon in normal messages. Detailed errors may still be shown because recovery work needs traceability.

## Architecture

The GUI should live in a new module:

- `src/brawrec/gui.py`

The GUI calls the existing Python API directly rather than shelling out to the CLI:

- `parse_braw_layout`
- `visible_indexed_video_end`
- `scan_hidden_video`
- `build_repair_plan`
- `write_candidate`
- CLI/report helpers where practical, or report writers directly.

Long operations run on a background thread so the window stays responsive. The GUI must disable action buttons while a task is running and re-enable them afterward.

## Safety

The source `.braw` is opened read-only by existing recovery functions. The GUI must never overwrite the source. If the candidate already exists, the app should refuse and ask the user to choose a different output path or remove the old candidate manually.

Reports are written next to the candidate in the selected output folder:

- `analysis.json`
- `analysis.md`
- `repair.json`
- `repair.md`
- `verify.json`
- `verify.md`

## Packaging

The first package target is a PyInstaller one-file executable:

- `dist/BRAW Recovery.exe`

The project should also keep a simple source launch path for development:

```powershell
$env:PYTHONPATH="src"
python -c "from brawrec.gui import main; main()"
```

## Testing

Automated tests cover the non-visual GUI helpers where possible, especially:

- Default output folder and candidate path generation.
- Refusal when source and candidate paths resolve to the same file.
- Report payload creation through existing core functions remains covered by current CLI/recovery tests.

Manual smoke checks cover:

- Opening the window.
- Running analyze on known C007/C009 fixtures.
- Running repair and verify on C007/C009.
- Confirming candidates remain separate files.
