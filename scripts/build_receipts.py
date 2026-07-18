"""Regenerate — and VERIFY — the frozen receipts slice from upstream ICDAR-SROIE.

OPT-IN / VERIFICATION ONLY. This script is NOT on the offline demo path:
`run_blind.py` reads the committed `data/receipts.json` with no network and never
imports this module. It exists so a reviewer can independently confirm the frozen
slice was built by a stated rule and not cherry-picked.

Provenance & filter (this filter is the thing being trusted):
  Source: https://github.com/zzzDavid/ICDAR-2019-SROIE  (dirs data/box, data/key)
  626 receipts upstream. A receipt is INCLUDED iff BOTH:
    - key/<id>.json "total" is a clean money value matching ^\\d{1,6}\\.\\d{2}$
      (no currency prefix, no thousands comma), AND
    - box/<id>.csv yields >= 5 OCR text lines.
  That leaves exactly 535. Records are sorted by id; the first 120 are the DEV
  cohort the rules were tuned on, the remaining 415 are held-out.
  Each record = {"id", "lines", "true_total"}, where `lines` is the text field
  (everything after the 8 bounding-box coords) of each box row, in file order.

Usage:
  # fetch upstream text data (sparse clone skips the large images):
  git clone --depth 1 --filter=blob:none --sparse \\
      https://github.com/zzzDavid/ICDAR-2019-SROIE.git /tmp/sroie
  git -C /tmp/sroie sparse-checkout set data

  python scripts/build_receipts.py --upstream /tmp/sroie          # verify (default)
  python scripts/build_receipts.py --upstream /tmp/sroie --write  # regenerate file

Verify mode rebuilds the slice and compares it BYTE-FOR-BYTE against the committed
data/receipts.json, exiting non-zero on any mismatch. One command, yes/no answer.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CLEAN_TOTAL = re.compile(r"^\d{1,6}\.\d{2}$")
MIN_LINES = 5

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROZEN = os.path.join(REPO_ROOT, "data", "receipts.json")


def _read(path: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return open(path, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    return open(path, encoding="latin-1", errors="replace").read()


def _box_lines(path: str) -> list:
    """Text field (after the 8 bbox coords) of each non-empty box row, in order."""
    out = []
    for row in _read(path).splitlines():
        if not row.strip():
            continue
        parts = row.split(",", 8)
        if len(parts) < 9:
            continue
        out.append(parts[8])
    return out


def _data_dir(upstream: str) -> str:
    """Accept either the repo root (…/data/box) or a directory holding box/key."""
    for cand in (os.path.join(upstream, "data"), upstream):
        if os.path.isdir(os.path.join(cand, "box")) and os.path.isdir(os.path.join(cand, "key")):
            return cand
    sys.exit(f"error: no box/ and key/ dirs found under {upstream!r} "
             f"(expected an ICDAR-2019-SROIE clone)")


def build(upstream: str) -> list:
    """Rebuild the slice from an upstream clone, applying the stated filter."""
    data = _data_dir(upstream)
    key_dir, box_dir = os.path.join(data, "key"), os.path.join(data, "box")
    ids = sorted(os.path.splitext(f)[0] for f in os.listdir(key_dir) if f.endswith(".json"))

    recs = []
    for rid in ids:
        try:
            key = json.loads(_read(os.path.join(key_dir, f"{rid}.json")))
        except json.JSONDecodeError:
            continue
        total = str(key.get("total", "")).strip()
        if not CLEAN_TOTAL.match(total):
            continue
        box_path = os.path.join(box_dir, f"{rid}.csv")
        if not os.path.exists(box_path):
            continue
        lines = _box_lines(box_path)
        if len(lines) < MIN_LINES:
            continue
        recs.append({"id": rid, "lines": lines, "true_total": total})

    recs.sort(key=lambda r: r["id"])
    return recs


def serialize(recs: list) -> bytes:
    """Canonical on-disk form — must match how data/receipts.json was written."""
    return json.dumps(recs, indent=0, ensure_ascii=False).encode("utf-8")


def _structural_diff(built: list, frozen: list) -> list:
    """Human-readable id-level differences, for when bytes don't match."""
    diffs = []
    b, f = {r["id"]: r for r in built}, {r["id"]: r for r in frozen}
    only_built, only_frozen = set(b) - set(f), set(f) - set(b)
    if only_built:
        diffs.append(f"{len(only_built)} id(s) only in rebuild: {sorted(only_built)[:10]}")
    if only_frozen:
        diffs.append(f"{len(only_frozen)} id(s) only in committed: {sorted(only_frozen)[:10]}")
    for rid in sorted(set(b) & set(f)):
        if b[rid]["lines"] != f[rid]["lines"]:
            diffs.append(f"{rid}: lines differ")
        elif str(b[rid]["true_total"]) != str(f[rid]["true_total"]):
            diffs.append(f"{rid}: total {b[rid]['true_total']} vs {f[rid]['true_total']}")
    return diffs


def verify(upstream: str) -> bool:
    built = build(upstream)
    built_bytes = serialize(built)
    frozen_bytes = open(FROZEN, "rb").read()
    if built_bytes == frozen_bytes:
        print(f"PASS — rebuilt {len(built)} receipts from upstream; "
              f"byte-identical to committed data/receipts.json")
        return True
    print(f"FAIL — rebuild ({len(built)} receipts) does NOT match committed "
          f"data/receipts.json ({len(json.loads(frozen_bytes))} receipts)")
    for line in _structural_diff(built, json.loads(frozen_bytes))[:20]:
        print(f"  {line}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate/verify the frozen receipts slice.")
    ap.add_argument("--upstream", required=True,
                    help="path to an ICDAR-2019-SROIE clone (holding data/box, data/key)")
    ap.add_argument("--write", action="store_true",
                    help="overwrite data/receipts.json instead of verifying")
    args = ap.parse_args()

    if args.write:
        recs = build(args.upstream)
        open(FROZEN, "wb").write(serialize(recs))
        print(f"wrote {len(recs)} receipts to {FROZEN}")
        return 0
    return 0 if verify(args.upstream) else 1


if __name__ == "__main__":
    sys.exit(main())
