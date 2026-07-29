#!/usr/bin/env python3
"""
Remove the z-based flow constraints from CMST AvV+U, producing AvV+U-z.

Stage 3 of 3 in the CMST pipeline:

    .dat  -->  AvV  -->  AvV+U  --[this script]-->  AvV+U-z

The AvV+U file states flow conservation twice: once over the binary z
variables (added in stage 1) and once over the aggregated u/w variables
(added in stage 2). This script deletes the former, leaving flow conservation
expressed only in the aggregated variables.

Which constraints are the z-based flow constraints?
---------------------------------------------------
cmst_build_lp.py emits, in order:

    c1        .. cn      in-degree constraints
    c(n+1)    .. c2n     flow constraints in terms of z     <-- deleted here

so the target range is c(n+1) .. c2n and is derived from n rather than
hard-coded. For the paper's instances (n = 80) this is c81..c160, which
reproduces the committed data exactly.

Usage
-----
    python cmst_make_avv_u_minus_z.py --input-dir out/AvV+U --output-dir out/AvV+U-z
"""

import argparse
import re
import sys
from pathlib import Path

Z_VAR = re.compile(r"\bz\.(\d+)\.(\d+)\.(\d+)\b")
CONSTRAINT_START = re.compile(r"^\s*c(\d+)\s*:")
SECTION = re.compile(
    r"^\s*(Bounds|Binaries|Binary|Bin|Generals|General|Gen|Integers|End|"
    r"Subject\s+To|st|Minimize|Maximize)\b",
    re.IGNORECASE,
)


def detect_n(lp_path):
    """Largest vertex index appearing in the z.i.j.k variables."""
    n = 0
    with open(lp_path, "r") as f:
        for line in f:
            for i, j, _ in Z_VAR.findall(line):
                n = max(n, int(i), int(j))
    if n == 0:
        raise ValueError(f"{lp_path}: could not infer n (no z.i.j.k variables found)")
    return n


def delete_constraint_range(lines, start_id, end_id):
    """Drop every constraint block whose id lies in [start_id, end_id].

    A constraint block starts at a line matching 'cN:' and runs until the next
    constraint start or the next LP section keyword, so constraints wrapped
    across several lines are removed in full.
    """
    out = []
    deleting = False
    removed = 0
    for line in lines:
        m = CONSTRAINT_START.match(line)
        if m:
            cid = int(m.group(1))
            deleting = start_id <= cid <= end_id
            if deleting:
                removed += 1
                continue
        elif SECTION.match(line):
            deleting = False
        if not deleting:
            out.append(line)
    return out, removed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", required=True, help="directory of AvV+U .lp files")
    ap.add_argument("--output-dir", required=True, help="directory to write AvV+U-z .lp files")
    ap.add_argument("--n", type=int, default=None, help="override inferred n")
    args = ap.parse_args()

    in_dir, out_dir = Path(args.input_dir), Path(args.output_dir)
    if not in_dir.is_dir():
        sys.exit(f"error: not a directory: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    lp_files = sorted(in_dir.glob("*.lp"))
    if not lp_files:
        sys.exit(f"error: no .lp files in {in_dir}")

    for lp in lp_files:
        n = args.n if args.n is not None else detect_n(lp)
        start_id, end_id = n + 1, 2 * n
        lines = open(lp, "r").readlines()
        new_lines, removed = delete_constraint_range(lines, start_id, end_id)
        (out_dir / lp.name).write_text("".join(new_lines))
        flag = "" if removed == n else f"  WARNING: expected {n}"
        print(f"{lp.name}: n={n} removed c{start_id}-c{end_id} ({removed} constraints){flag}")

    print(f"\nwrote {len(lp_files)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
