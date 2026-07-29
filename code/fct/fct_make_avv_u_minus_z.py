#!/usr/bin/env python3
"""
Remove the z-based flow constraints from FCT AvV+U, producing AvV+U-z.

    AvV  -->  AvV+U  --[this script]-->  AvV+U-z

The AvV+U file states flow conservation twice: once over the binary z
variables (emitted by fctgen2) and once over the aggregated u/w variables
(added by fct_add_aggregation.py). This script deletes the former, leaving flow
conservation expressed only in the aggregated variables.

Note the difference from fct_make_avv_minus_z.py: there the z-based flow
constraints are REPLACED by equivalent x-based ones, because nothing else in
the AvV file constrains the flow. Here they are simply DELETED, because the
aggregated u/w constraints already serve that role.

Which constraints are the z-based flow constraints?
---------------------------------------------------
fctgen2 emits 3n^2 binarization constraints followed by the 2n flow
constraints, so the target range is

    c(3n^2 + 1)  ..  c(3n^2 + 2n)

derived from n rather than hard-coded. For the paper's instances this gives
c2701..c2760 (n=30) and c4801..c4880 (n=40), which reproduces the committed
data exactly. Override with --start-id/--end-id if you need a different range.

Usage
-----
    python fct_make_avv_u_minus_z.py \
        --input-dir  data_instances/FCTP/allfiles/AvV_plus_U \
        --output-dir out/AvV_plus_U_minus_z
"""

import argparse
import re
import sys
from pathlib import Path

CONSTRAINT_START = re.compile(r"^\s*c(\d+)\s*:")
SECTION = re.compile(
    r"^\s*(Bounds|Binaries|Binary|Bin|Generals|General|Gen|Integers|End|"
    r"Subject\s+To|st|Minimize|Maximize)\b",
    re.IGNORECASE,
)


def extract_n(filename):
    """First numeric field of the filename, i.e. the number of supply nodes."""
    for part in filename.split("_"):
        if part.isdigit():
            return int(part)
    return None


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
    ap.add_argument("--input-dir", required=True,
                    help="directory of AvV+U files (z2fctWithUW_*.lp)")
    ap.add_argument("--output-dir", required=True,
                    help="directory to write AvV+U-z files")
    ap.add_argument("--output-prefix", default="avv-z",
                    help="filename prefix for outputs (default: avv-z)")
    ap.add_argument("--n", type=int, default=None, help="override n inferred from filename")
    ap.add_argument("--start-id", type=int, default=None, help="override first flow constraint id")
    ap.add_argument("--end-id", type=int, default=None, help="override last flow constraint id")
    args = ap.parse_args()

    in_dir, out_dir = Path(args.input_dir), Path(args.output_dir)
    if not in_dir.is_dir():
        sys.exit(f"error: not a directory: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    lp_files = sorted(in_dir.glob("*.lp"))
    if not lp_files:
        sys.exit(f"error: no .lp files in {in_dir}")

    for lp in lp_files:
        n = args.n if args.n is not None else extract_n(lp.name)
        if n is None:
            sys.exit(f"error: {lp.name}: could not extract n from filename; pass --n")
        start_id = args.start_id if args.start_id is not None else 3 * n * n + 1
        end_id = args.end_id if args.end_id is not None else 3 * n * n + 2 * n

        ident = lp.name.rsplit(".lp", 1)[0].split("_", 1)[1]
        out_name = f"{args.output_prefix}_{ident}.lp"

        lines = open(lp, "r").readlines()
        new_lines, removed = delete_constraint_range(lines, start_id, end_id)
        (out_dir / out_name).write_text("".join(new_lines))

        flag = "" if removed == 2 * n else f"  WARNING: expected {2 * n}"
        print(f"{lp.name}: n={n} removed c{start_id}-c{end_id} ({removed} constraints)"
              f" -> {out_name}{flag}")

    print(f"\nwrote {len(lp_files)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
