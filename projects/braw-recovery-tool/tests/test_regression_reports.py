from pathlib import Path


README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_documents_c007_and_c009_regression_commands_and_counts():
    text = README.read_text(encoding="utf-8")

    for command in (
        "brawrec analyze D:\\AI\\braw_forensics\\F004\\F004_02200341_C007.braw --out D:\\AI\\braw-recovery-tool\\runs\\C007",
        "brawrec repair D:\\AI\\braw_forensics\\F004\\F004_02200341_C007.braw --out D:\\AI\\braw-recovery-tool\\runs\\C007\\C007_candidate.braw --report D:\\AI\\braw-recovery-tool\\runs\\C007",
        "brawrec verify D:\\AI\\braw-recovery-tool\\runs\\C007\\C007_candidate.braw --out D:\\AI\\braw-recovery-tool\\runs\\C007",
        "brawrec analyze D:\\AI\\braw_forensics\\C022_new\\C022_07042240_C009.braw --out D:\\AI\\braw-recovery-tool\\runs\\C009",
        "brawrec repair D:\\AI\\braw_forensics\\C022_new\\C022_07042240_C009.braw --out D:\\AI\\braw-recovery-tool\\runs\\C009\\C009_candidate.braw --report D:\\AI\\braw-recovery-tool\\runs\\C009",
        "brawrec verify D:\\AI\\braw-recovery-tool\\runs\\C009\\C009_candidate.braw --out D:\\AI\\braw-recovery-tool\\runs\\C009",
        "C007: `756 -> 881` video frames, `+125` hidden frames.",
        "C009: `1638 -> 1662` video frames, `+24` hidden frames.",
    ):
        assert command in text
