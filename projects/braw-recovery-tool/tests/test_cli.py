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
