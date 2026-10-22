# BRAW Recovery Tool

Forensic-safe Blackmagic RAW recovery CLI.

## Regression Checks

Run these end-to-end checks against the known recovery cases. The source files are
opened read-only, and each repair writes a separate candidate file.

### C007

```text
brawrec analyze D:\AI\braw_forensics\F004\F004_02200341_C007.braw --out D:\AI\braw-recovery-tool\runs\C007
brawrec repair D:\AI\braw_forensics\F004\F004_02200341_C007.braw --out D:\AI\braw-recovery-tool\runs\C007\C007_candidate.braw --report D:\AI\braw-recovery-tool\runs\C007
brawrec verify D:\AI\braw-recovery-tool\runs\C007\C007_candidate.braw --out D:\AI\braw-recovery-tool\runs\C007
```

Expected: C007: `756 -> 881` video frames, `+125` hidden frames.

### C009

```text
brawrec analyze D:\AI\braw_forensics\C022_new\C022_07042240_C009.braw --out D:\AI\braw-recovery-tool\runs\C009
brawrec repair D:\AI\braw_forensics\C022_new\C022_07042240_C009.braw --out D:\AI\braw-recovery-tool\runs\C009\C009_candidate.braw --report D:\AI\braw-recovery-tool\runs\C009
brawrec verify D:\AI\braw-recovery-tool\runs\C009\C009_candidate.braw --out D:\AI\braw-recovery-tool\runs\C009
```

Expected: C009: `1638 -> 1662` video frames, `+24` hidden frames.

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
