"""`wobbly run <file>` — batch over a dataset defined in a file."""
import json
import textwrap

import pytest

from wobbly.cli import main

DATASET = """
from wobbly import order_invariant
system = lambda m: m["options"][0]          # first-option bias -> flags
inputs = [{"options": ["a", "b", "c"]}, {"options": ["x", "y", "z"]}]
relations = [order_invariant(field="options")]
"""


def _write(tmp_path, body):
    p = tmp_path / "ds.py"
    p.write_text(textwrap.dedent(body))
    return str(p)


def test_run_summary(tmp_path, capsys):
    rc = main(["run", _write(tmp_path, DATASET), "--samples", "10", "--baseline", "1"])
    out = capsys.readouterr().out.lower()
    assert "flagged" in out
    assert rc == 0


def test_run_json_is_valid(tmp_path, capsys):
    rc = main(["run", _write(tmp_path, DATASET), "--json", "--samples", "10", "--baseline", "1"])
    d = json.loads(capsys.readouterr().out)
    assert d["n"] == 2 and d["flagged"] == [0, 1]
    assert rc == 0


def test_run_fail_on_flag_exit_code(tmp_path, capsys):
    rc = main(["run", _write(tmp_path, DATASET), "--fail-on-flag", "--samples", "10", "--baseline", "1"])
    assert rc == 1


def test_run_missing_system_errors(tmp_path):
    body = "inputs = []\nrelations = []\n"           # no system
    with pytest.raises(SystemExit):
        main(["run", _write(tmp_path, body)])
