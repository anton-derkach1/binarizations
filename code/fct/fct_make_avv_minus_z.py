#!/usr/bin/env python3
"""
Rewrite the FCT flow constraints from z variables to x variables, producing AvV-z.

    fctgen2 -o 2  -->  AvV  --[this script]-->  AvV-z

fctgen2 emits the AvV formulation with flow conservation stated over the binary
z variables only; the continuous x variables carry no flow constraints of their
own. AvV-z is the AvV formulation with those z-based flow constraints REPLACED
by the equivalent constraints over x, so each is rewritten rather than deleted:

    supply i (<=):   z.i.0.1 + 2 z.i.0.2 + ...  <=  s_i
              -->   x.i.0 + x.i.1 + ... + x.i.(n-1)  <=  s_i

    demand j  (=):   z.0.j.1 + 2 z.0.j.2 + ...   =  d_j
              -->   x.0.j + x.1.j + ... + x.(n-1).j   =  d_j

The right-hand side and the constraint number are preserved, so the file keeps
the same constraint count and numbering as AvV.

Which constraints are the z-based flow constraints?
---------------------------------------------------
fctgen2 emits, in order, 3n^2 constraints defining the binarization, then the
2n flow constraints (n supply, then n demand). The target range is therefore

    c(3n^2 + 1)  ..  c(3n^2 + 2n)

derived from n rather than hard-coded. For the paper's instances this gives
c2701..c2760 (n=30) and c4801..c4880 (n=40), which reproduces the committed
data exactly. Override with --start-id/--end-id if you need a different range.

Usage
-----
    python fct_make_avv_minus_z.py \
        --input-dir  data_instances/FCTP/allfiles/AvV \
        --output-dir out/AvV-z
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
Z_TERM = re.compile(r"z\.(\d+)\.(\d+)\.(\d+)")
RHS = re.compile(r"(<=|>=|=)\s*(\S+)")


def extract_n(filename):
    """First numeric field of the filename, i.e. the number of supply nodes."""
    for part in filename.split("_"):
        if part.isdigit():
            return int(part)
    return None


def iter_blocks(lines):
    """Yield (constraint_id_or_None, [lines]) covering the whole file in order.

    A constraint block starts at a line matching 'cN:' and runs until the next
    constraint start or the next LP section keyword, so constraints wrapped
    across several lines are handled in full.
    """
    cid, buf = None, []
    for line in lines:
        m = CONSTRAINT_START.match(line)
        if m:
            if buf:
                yield cid, buf
            cid, buf = int(m.group(1)), [line]
        elif SECTION.match(line):
            if buf:
                yield cid, buf
            cid, buf = None, [line]
        else:
            buf.append(line)
    if buf:
        yield cid, buf


def rewrite_block(cid, block, n):
    """Replace a z-based flow constraint with the equivalent x-based one."""
    text = " ".join(" ".join(block).split())

    m_rhs = RHS.search(text)
    if not m_rhs:
        return None
    operator, rhs = m_rhs.group(1), m_rhs.group(2)

    z_terms = Z_TERM.findall(text)
    if not z_terms:
        return None

    if operator == "<=":
        # supply constraint: all arcs out of a fixed supply node
        i = int(z_terms[0][0])
        x_terms = [f"x.{i}.{j}" for j in range(n)]
    elif operator == "=":
        # demand constraint: all arcs into a fixed demand node
        j = int(z_terms[0][1])
        x_terms = [f"x.{i}.{j}" for i in range(n)]
    else:
        return None

    return f"c{cid}: " + " + ".join(x_terms) + f" {operator} {rhs}\n"


def transform(lp_path, out_path, n, start_id, end_id):
    lines = open(lp_path, "r").readlines()
    out, rewritten = [], 0
    for cid, block in iter_blocks(lines):
        if cid is not None and start_id <= cid <= end_id:
            new = rewrite_block(cid, block, n)
            if new is not None:
                out.append(new)
                rewritten += 1
                continue
        out.extend(block)
    out_path.write_text("".join(out))
    return rewritten


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", required=True, help="directory of AvV files (z2fct_*.lp)")
    ap.add_argument("--output-dir", required=True, help="directory to write AvV-z files")
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

        count = transform(lp, out_dir / out_name, n, start_id, end_id)
        flag = "" if count == 2 * n else f"  WARNING: expected {2 * n}"
        print(f"{lp.name}: n={n} rewrote c{start_id}-c{end_id} ({count} constraints)"
              f" -> {out_name}{flag}")

    print(f"\nwrote {len(lp_files)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
