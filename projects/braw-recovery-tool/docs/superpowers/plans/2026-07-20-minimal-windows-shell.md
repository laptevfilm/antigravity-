# Minimal Windows Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal Tkinter Windows shell for BRAW Recovery and package it as `BRAW Recovery.exe` when PyInstaller is available.

**Architecture:** Keep the recovery core unchanged. Add small GUI workflow helpers for paths and report calls, then add a Tkinter window that calls those helpers on a background thread. Add packaging metadata and a build script that produces a one-file Windows executable.

**Tech Stack:** Python 3.12, Tkinter from the Python standard library, existing `brawrec` recovery modules, PyInstaller for the executable build.

## Global Constraints

- The GUI must never overwrite the source `.braw`.
- The source `.braw` must remain read-only; repair writes a separate candidate file.
- Default output folder is `runs/<source-stem>` under the project folder.
- Default candidate path is `<source-stem>_candidate.braw` inside the selected output folder.
- Reports are written next to the candidate in the selected output folder.
- Long operations must run on a background thread so the window stays responsive.
- Normal GUI messages should avoid technical jargon, while detailed errors may still be shown for traceability.
- First package target is `dist/BRAW Recovery.exe`.

---

## File Structure

- Create `src/brawrec/gui_workflows.py`: non-visual path helpers and direct calls into existing analyze, repair, and verify report functions.
- Create `src/brawrec/gui.py`: Tkinter window, widgets, background task runner, log/status updates, and `main()`.
- Create `tests/test_gui_workflows.py`: automated tests for default paths and source/candidate safety checks.
- Modify `pyproject.toml`: add `brawrec-gui = "brawrec.gui:main"` script entry point.
- Modify `README.md`: document GUI source launch and executable build/use.
- Create `tools/build_windows_exe.ps1`: PyInstaller build command for `dist/BRAW Recovery.exe`.

---

### Task 1: GUI Workflow Helpers

**Files:**
- Create: `src/brawrec/gui_workflows.py`
- Create: `tests/test_gui_workflows.py`

**Interfaces:**
- Consumes: existing `_write_analysis_reports(source: Path, report_dir: Path)`, `_repair(source: Path, output: Path, report_dir: Path)`, `_verify(candidate: Path, report_dir: Path)` from `brawrec.cli`.
- Produces:
  - `project_root() -> Path`
  - `default_output_dir(source: Path, root: Path | None = None) -> Path`
  - `default_candidate_path(source: Path, output_dir: Path) -> Path`
  - `validate_candidate_path(source: Path, candidate: Path) -> None`
  - `analyze_source(source: Path, output_dir: Path) -> dict`
  - `recover_source(source: Path, candidate: Path, report_dir: Path) -> dict`
  - `verify_candidate(candidate: Path, output_dir: Path) -> dict`

- [ ] **Step 1: Write failing tests**

Add `tests/test_gui_workflows.py`:

```python
from pathlib import Path

import pytest

from brawrec.gui_workflows import (
    default_candidate_path,
    default_output_dir,
    validate_candidate_path,
)


def test_default_output_dir_uses_runs_and_source_stem(tmp_path: Path):
    source = tmp_path / "Clip Name.braw"
    root = tmp_path / "project"

    assert default_output_dir(source, root) == root / "runs" / "Clip Name"


def test_default_candidate_path_uses_source_stem(tmp_path: Path):
    source = tmp_path / "A001_010101.braw"
    output_dir = tmp_path / "runs" / "A001_010101"

    assert default_candidate_path(source, output_dir) == output_dir / "A001_010101_candidate.braw"


def test_validate_candidate_path_rejects_source_path(tmp_path: Path):
    source = tmp_path / "clip.braw"
    source.write_bytes(b"sample")

    with pytest.raises(ValueError, match="same as the source"):
        validate_candidate_path(source, source)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_gui_workflows.py -q
```

Expected: FAIL because `brawrec.gui_workflows` does not exist.

- [ ] **Step 3: Implement workflow helpers**

Create `src/brawrec/gui_workflows.py`:

```python
from __future__ import annotations

from pathlib import Path

from brawrec.cli import _repair, _verify, _write_analysis_reports


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_output_dir(source: Path, root: Path | None = None) -> Path:
    base = project_root() if root is None else root
    return base / "runs" / source.stem


def default_candidate_path(source: Path, output_dir: Path) -> Path:
    return output_dir / f"{source.stem}_candidate.braw"


def validate_candidate_path(source: Path, candidate: Path) -> None:
    if source.resolve() == candidate.resolve():
        raise ValueError("candidate path is the same as the source")


def analyze_source(source: Path, output_dir: Path) -> dict:
    return _write_analysis_reports(source, output_dir)


def recover_source(source: Path, candidate: Path, report_dir: Path) -> dict:
    validate_candidate_path(source, candidate)
    _repair(source, candidate, report_dir)
    return {"candidate": str(candidate.resolve()), "report_dir": str(report_dir.resolve())}


def verify_candidate(candidate: Path, output_dir: Path) -> dict:
    _verify(candidate, output_dir)
    return {"candidate": str(candidate.resolve()), "report_dir": str(output_dir.resolve())}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests\test_gui_workflows.py -q
```

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\brawrec\gui_workflows.py tests\test_gui_workflows.py
git commit -m "feat: add GUI recovery workflow helpers"
```

---

### Task 2: Minimal Tkinter App

**Files:**
- Create: `src/brawrec/gui.py`
- Test: `tests/test_gui_workflows.py`

**Interfaces:**
- Consumes:
  - `default_output_dir(source: Path, root: Path | None = None) -> Path`
  - `default_candidate_path(source: Path, output_dir: Path) -> Path`
  - `analyze_source(source: Path, output_dir: Path) -> dict`
  - `recover_source(source: Path, candidate: Path, report_dir: Path) -> dict`
  - `verify_candidate(candidate: Path, output_dir: Path) -> dict`
- Produces:
  - `BrawRecoveryApp`
  - `main() -> None`

- [ ] **Step 1: Write import smoke test**

Append to `tests/test_gui_workflows.py`:

```python
def test_gui_module_imports_without_opening_window():
    from brawrec import gui

    assert gui.BrawRecoveryApp is not None
    assert callable(gui.main)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests\test_gui_workflows.py::test_gui_module_imports_without_opening_window -q
```

Expected: FAIL because `brawrec.gui` does not exist.

- [ ] **Step 3: Implement Tkinter window**

Create `src/brawrec/gui.py` with:

```python
from __future__ import annotations

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from brawrec.gui_workflows import (
    analyze_source,
    default_candidate_path,
    default_output_dir,
    recover_source,
    verify_candidate,
)


class BrawRecoveryApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BRAW Recovery")
        self.root.geometry("760x520")
        self.root.minsize(680, 440)

        self.source_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.candidate_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.buttons: list[ttk.Button] = []

        self._build()
        self.root.after(100, self._drain_messages)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        ttk.Label(frame, text="Source BRAW").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse...", command=self._choose_source).grid(row=0, column=2)

        ttk.Label(frame, text="Output folder").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Browse...", command=self._choose_output).grid(row=1, column=2)

        ttk.Label(frame, text="Candidate").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.candidate_var).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(frame, text="Reset", command=self._refresh_candidate).grid(row=2, column=2)

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 8))
        for text, command in (
            ("Analyze", self._run_analyze),
            ("Recover", self._run_recover),
            ("Verify", self._run_verify),
        ):
            button = ttk.Button(actions, text=text, command=command)
            button.pack(side=tk.LEFT, padx=(0, 8))
            self.buttons.append(button)

        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky="w")
        self.log = tk.Text(frame, height=14, wrap="word")
        self.log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))

    def _choose_source(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose BRAW file",
            filetypes=[("Blackmagic RAW", "*.braw"), ("All files", "*.*")],
        )
        if not selected:
            return
        source = Path(selected)
        output = default_output_dir(source)
        self.source_var.set(str(source))
        self.output_var.set(str(output))
        self.candidate_var.set(str(default_candidate_path(source, output)))

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if not selected:
            return
        self.output_var.set(selected)
        self._refresh_candidate()

    def _refresh_candidate(self) -> None:
        source = self._source_path()
        output = self._output_dir()
        if source is None or output is None:
            return
        self.candidate_var.set(str(default_candidate_path(source, output)))

    def _run_analyze(self) -> None:
        source = self._require_source()
        output = self._require_output()
        if source and output:
            self._run_task("Analyzing...", lambda: analyze_source(source, output), "Analysis complete.")

    def _run_recover(self) -> None:
        source = self._require_source()
        output = self._require_output()
        candidate = self._require_candidate()
        if source and output and candidate:
            self._run_task("Recovering...", lambda: recover_source(source, candidate, output), "Recovery complete.")

    def _run_verify(self) -> None:
        output = self._require_output()
        candidate = self._require_candidate()
        if output and candidate:
            self._run_task("Verifying...", lambda: verify_candidate(candidate, output), "Verification complete.")

    def _run_task(self, busy: str, worker, success: str) -> None:
        self.status_var.set(busy)
        self._set_buttons(False)
        self._append_log(busy)

        def target() -> None:
            try:
                result = worker()
            except Exception as exc:
                self.messages.put(("error", str(exc)))
            else:
                self.messages.put(("success", f"{success}\n{result}"))

        threading.Thread(target=target, daemon=True).start()

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, text = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "error":
                self.status_var.set("Stopped")
                self._append_log(f"Stopped: {text}")
                messagebox.showerror("BRAW Recovery", text)
            else:
                self.status_var.set("Ready")
                self._append_log(text)
            self._set_buttons(True)
        self.root.after(100, self._drain_messages)

    def _set_buttons(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self.buttons:
            button.configure(state=state)

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text + "\n\n")
        self.log.see(tk.END)

    def _source_path(self) -> Path | None:
        value = self.source_var.get().strip()
        return Path(value) if value else None

    def _output_dir(self) -> Path | None:
        value = self.output_var.get().strip()
        return Path(value) if value else None

    def _candidate_path(self) -> Path | None:
        value = self.candidate_var.get().strip()
        return Path(value) if value else None

    def _require_source(self) -> Path | None:
        source = self._source_path()
        if source is None:
            messagebox.showwarning("BRAW Recovery", "Choose a source BRAW file first.")
            return None
        return source

    def _require_output(self) -> Path | None:
        output = self._output_dir()
        if output is None:
            messagebox.showwarning("BRAW Recovery", "Choose an output folder first.")
            return None
        return output

    def _require_candidate(self) -> Path | None:
        candidate = self._candidate_path()
        if candidate is None:
            messagebox.showwarning("BRAW Recovery", "Choose a candidate file path first.")
            return None
        return candidate


def main() -> None:
    root = tk.Tk()
    BrawRecoveryApp(root)
    root.mainloop()
```

- [ ] **Step 4: Run import smoke test**

Run:

```powershell
python -m pytest tests\test_gui_workflows.py::test_gui_module_imports_without_opening_window -q
```

Expected: PASS.

- [ ] **Step 5: Run full tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src\brawrec\gui.py tests\test_gui_workflows.py
git commit -m "feat: add minimal Tkinter shell"
```

---

### Task 3: Packaging And Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `tools/build_windows_exe.ps1`

**Interfaces:**
- Consumes: `brawrec.gui:main`
- Produces:
  - console script `brawrec-gui`
  - build script `tools/build_windows_exe.ps1`
  - package output `dist/BRAW Recovery.exe`

- [ ] **Step 1: Add GUI script entry point**

Modify `pyproject.toml`:

```toml
[project.scripts]
brawrec = "brawrec.cli:console_main"
brawrec-gui = "brawrec.gui:main"
```

- [ ] **Step 2: Add build script**

Create `tools/build_windows_exe.ps1`:

```powershell
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m PyInstaller `
  --name "BRAW Recovery" `
  --onefile `
  --windowed `
  --paths "$ProjectRoot\src" `
  --distpath "$ProjectRoot\dist" `
  --workpath "$ProjectRoot\build\pyinstaller" `
  --specpath "$ProjectRoot\build" `
  "$ProjectRoot\src\brawrec\gui.py"

Write-Host "Built: $ProjectRoot\dist\BRAW Recovery.exe"
```

- [ ] **Step 3: Update README**

Append this section to `README.md`:

```markdown
## Minimal Windows App

Development launch:

```powershell
cd "D:\AI\BRAW Recovery"
$env:PYTHONPATH="src"
python -c "from brawrec.gui import main; main()"
```

Build the Windows executable:

```powershell
cd "D:\AI\BRAW Recovery"
.\tools\build_windows_exe.ps1
```

The executable is written to:

```text
D:\AI\BRAW Recovery\dist\BRAW Recovery.exe
```
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Build executable**

First check whether PyInstaller is available:

```powershell
python -m PyInstaller --version
```

If available, run:

```powershell
.\tools\build_windows_exe.ps1
```

Expected: `dist\BRAW Recovery.exe` exists.

If PyInstaller is missing, install it with user approval:

```powershell
python -m pip install pyinstaller
```

Then rerun:

```powershell
.\tools\build_windows_exe.ps1
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add pyproject.toml README.md tools\build_windows_exe.ps1
git commit -m "build: add Windows GUI executable packaging"
```

---

### Task 4: Manual Smoke Verification

**Files:**
- Modify: `.superpowers/sdd/progress.md`

**Interfaces:**
- Consumes: `dist/BRAW Recovery.exe`
- Produces: documented smoke results for C007/C009.

- [ ] **Step 1: Launch source GUI**

Run:

```powershell
$env:PYTHONPATH="src"
python -c "from brawrec.gui import main; main()"
```

Expected: a window titled `BRAW Recovery` opens.

- [ ] **Step 2: Launch packaged GUI**

Run:

```powershell
& ".\dist\BRAW Recovery.exe"
```

Expected: a window titled `BRAW Recovery` opens.

- [ ] **Step 3: Verify core recovery remains green**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Run real CLI smoke after GUI changes**

Run:

```powershell
$env:PYTHONPATH="src"
python -c "from brawrec.cli import console_main; console_main()" analyze "D:\AI\braw_forensics\F004\F004_02200341_C007.braw" --out runs\C007-gui-smoke
python -c "from brawrec.cli import console_main; console_main()" repair "D:\AI\braw_forensics\F004\F004_02200341_C007.braw" --out runs\C007-gui-smoke\C007_candidate.braw --report runs\C007-gui-smoke
python -c "from brawrec.cli import console_main; console_main()" verify runs\C007-gui-smoke\C007_candidate.braw --out runs\C007-gui-smoke
```

Expected: C007 reports `+125` hidden frames and `881` final video frames.

- [ ] **Step 5: Update progress log**

Append to `.superpowers/sdd/progress.md`:

```markdown
Minimal Windows shell: complete; GUI source launch works, packaged executable built at dist/BRAW Recovery.exe, tests pass, C007 smoke remains 756 -> 881 (+125).
```

- [ ] **Step 6: Commit smoke note if tracked**

Run:

```powershell
git status --short
```

Expected: `.superpowers/sdd/progress.md` remains ignored. If it is tracked, commit it:

```powershell
git add .superpowers\sdd\progress.md
git commit -m "docs: record GUI smoke verification"
```

---

## Self-Review

- Spec coverage: Task 1 covers path defaults and source/candidate safety. Task 2 covers the compact Tkinter window, buttons, log, background thread, and direct API calls. Task 3 covers `BRAW Recovery.exe` packaging and README usage. Task 4 covers manual launch and real recovery smoke checks.
- Placeholder scan: no unfinished markers or unspecified error-handling steps remain.
- Type consistency: helper names in Task 2 match Task 1 exactly; script entry point matches `brawrec.gui:main`; build output matches `dist/BRAW Recovery.exe`.
