"""`wobbly judge` subcommand — loads a user's judge + cases and reports flips."""
import textwrap

import pytest

from wobbly.cli import main


def test_judge_demo_runs(capsys):
    rc = main(["judge"])                      # no file -> self-contained demo
    out = capsys.readouterr().out.lower()
    assert "flip" in out
    assert "no answer key" in out
    assert rc == 0


def test_judge_loads_user_file(capsys, tmp_path):
    p = tmp_path / "myjudge.py"
    p.write_text(textwrap.dedent('''
        judge = lambda case: "A"          # always first -> pure position bias
        cases = [{"question": "q", "answers": ["x", "y"]}]
    '''))
    rc = main(["judge", str(p)])
    out = capsys.readouterr().out.lower()
    assert "flip" in out
    assert rc == 0                            # default: report only, exit 0


def test_judge_fail_on_flip_exit_code(tmp_path, capsys):
    p = tmp_path / "j.py"
    p.write_text('judge = lambda case: "A"\ncases = [{"question": "q", "answers": ["x", "y"]}]\n')
    rc = main(["judge", str(p), "--fail-on-flip"])
    assert rc == 1                            # biased judge flips -> non-zero for CI


def test_judge_robust_judge_no_flip(tmp_path, capsys):
    p = tmp_path / "robust.py"
    # picks by content (shorter answer), independent of position -> no flip
    p.write_text('judge = lambda case: min(case["answers"], key=len)\n'
                 'cases = [{"question": "q", "answers": ["xx", "yyyy"]}]\n')
    rc = main(["judge", str(p), "--fail-on-flip"])
    assert rc == 0


def test_judge_missing_judge_errors(tmp_path):
    p = tmp_path / "bad.py"
    p.write_text('cases = [{"question": "q", "answers": ["x", "y"]}]\n')   # no judge
    with pytest.raises(SystemExit):
        main(["judge", str(p)])


def test_judge_file_not_found():
    with pytest.raises(SystemExit):
        main(["judge", "/no/such/file.py"])
