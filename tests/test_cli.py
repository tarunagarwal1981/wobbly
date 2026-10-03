from wobbly.cli import main


def test_version(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out.strip()
    from wobbly import __version__
    assert rc == 0
    assert out == __version__


def test_demo_runs_and_flags_order_bias(capsys):
    rc = main(["demo"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "violated" in out            # the built-in demo catches order bias


def test_no_command_prints_help_and_returns_nonzero(capsys):
    rc = main([])
    assert rc != 0
