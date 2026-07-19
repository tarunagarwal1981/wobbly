"""The `git clone && pytest` promise, two halves:

  1. the two-stage audit reproduces OFFLINE from the frozen slice, and
  2. that frozen slice is REGENERABLE from upstream by the stated filter.

If any pinned number below moves, this file is meant to fail — that is the
reproduction guarantee, and it forces the writeup's numbers to be updated in
lockstep with the code.
"""
import json
import os
import re

import pytest

import build_receipts
import run_blind
from wobbly import extract_total
from wobbly.relations import reorder_lines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sroie")
CLEAN = re.compile(r"^\d{1,6}\.\d{2}$")

# Honest, committed audit numbers per cohort: (n, total_wrong, flagged, wrong_flagged)
COHORTS = {
    "DEV": (120, 16, 2, 2),
    "HELD-OUT": (415, 116, 11, 8),
    "COMBINED": (535, 132, 13, 10),
}


@pytest.fixture(scope="module")
def receipts():
    return json.load(open(os.path.join(ROOT, "data", "receipts.json")))


# --------------------------------------------------------------------------
# dataset shape / provenance filter is visible in the committed data
# --------------------------------------------------------------------------
def test_dataset_shape(receipts):
    assert len(receipts) == 535
    assert [r["id"] for r in receipts] == sorted(r["id"] for r in receipts)
    for r in receipts:
        assert set(r) >= {"id", "lines", "true_total"}
        assert len(r["lines"]) >= 5                       # the >=5-lines filter
        assert CLEAN.match(str(r["true_total"]))          # the clean NN.NN filter


# --------------------------------------------------------------------------
# Promise 1 — the audit reproduces offline
# --------------------------------------------------------------------------
def _audit(cohort):
    flagged = run_blind.stage1_blind(cohort)
    return run_blind.stage2_audit(cohort, flagged)


def test_audit_reproduces(receipts):
    dev, held = receipts[: run_blind.DEV_N], receipts[run_blind.DEV_N :]
    for name, cohort in (("DEV", dev), ("HELD-OUT", held), ("COMBINED", receipts)):
        n, wrong, flagged, wrong_flagged = COHORTS[name]
        s = _audit(cohort)
        assert s["n"] == n, name
        assert s["total_wrong"] == wrong, name
        assert s["flagged"] == flagged, name
        assert s["wrong_flagged"] == wrong_flagged, name


def test_baseline_accuracy(receipts):
    wrong = 0
    for r in receipts:
        g = extract_total(r["lines"])
        if g is None or abs(g - float(r["true_total"])) > 0.011:
            wrong += 1
    assert wrong == 132                                   # 75% of 535


def test_run_blind_main_smoke(capsys):
    run_blind.main()
    out = capsys.readouterr().out
    assert "COMBINED" in out
    assert "HELD-OUT" in out
    assert "no labels read" in out


# --------------------------------------------------------------------------
# Stage 1 is BLIND — flags cannot depend on the ground-truth label
# --------------------------------------------------------------------------
def test_stage1_never_reads_label(receipts):
    sample = receipts[:80]
    base = {r["id"] for r, _ in run_blind.stage1_blind(sample)}
    # remove the label entirely: if any blind-stage code read it, this KeyErrors
    stripped = [{k: v for k, v in r.items() if k != "true_total"} for r in sample]
    after = {r["id"] for r, _ in run_blind.stage1_blind(stripped)}
    assert base == after


# --------------------------------------------------------------------------
# reorder relation is deterministic — the demo reproduces run-to-run
# --------------------------------------------------------------------------
def test_reorder_transform_deterministic(receipts):
    r = receipts[26]
    seq1 = [reorder_lines()(r)["lines"] for _ in range(8)]
    seq2 = [reorder_lines()(r)["lines"] for _ in range(8)]
    assert seq1 == seq2
    # and it actually reorders (not a no-op) on this receipt
    assert any(s != r["lines"] for s in seq1)


# --------------------------------------------------------------------------
# Promise 2 — the frozen slice is regenerable from upstream
# --------------------------------------------------------------------------
def test_slice_regenerable_from_fixture(receipts):
    """Build logic reproduces the committed records for the vendored ids,
    and applies the filter (030 has a '$8.20' total => excluded)."""
    built = build_receipts.build(FIXTURE)
    assert [r["id"] for r in built] == ["000", "001", "002"]   # 030 filtered out
    frozen = {r["id"]: r for r in receipts}
    for r in built:
        assert r["lines"] == frozen[r["id"]]["lines"]
        assert str(r["true_total"]) == str(frozen[r["id"]]["true_total"])


def test_serialize_roundtrip_matches_committed(receipts):
    """serialize(build(...)) is the exact on-disk form — so verify() is a true
    byte-identity check, not a lenient structural one."""
    frozen_bytes = open(os.path.join(ROOT, "data", "receipts.json"), "rb").read()
    assert build_receipts.serialize(receipts) == frozen_bytes


@pytest.mark.skipif(
    not os.environ.get("INVAR_SROIE"),
    reason="set INVAR_SROIE=<ICDAR-2019-SROIE clone> to byte-verify all 535",
)
def test_full_slice_regenerable_from_upstream():
    assert build_receipts.verify(os.environ["INVAR_SROIE"]) is True
