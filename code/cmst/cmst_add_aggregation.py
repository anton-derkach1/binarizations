#!/usr/bin/env python3
"""
Add aggregation variables to the CMST AvV formulation, producing AvV+U.

Stage 2 of 3 in the CMST pipeline:

    .dat  -->  AvV  --[this script]-->  AvV+U  -->  AvV+U-z

Two groups of constraints are appended to each input .lp file.

1. Definition of the aggregated variables

       u.i.k  =  sum_{j != i} z.i.j.k      (flow k leaving vertex i)
       w.j.k  =  sum_{i != j} z.i.j.k      (flow k entering vertex j)

   written in the file as  "- u.i.k + z.i.j1.k + z.i.j2.k + ... = 0".
   Only the root can push C units, so w.j.C reduces to z.0.j.C, and w.0.C
   does not exist.

2. Flow conservation restated in the aggregated variables

       sum_k k*w.i.k - sum_k k*u.i.k = 1   for each non-root vertex i

The original z-based constraints are left untouched; stage 3 removes them.

n and C are read from the .lp file itself (from the z.i.j.k index ranges), so
no editing of this script is required for other instance sizes. Override with
--n / --C if needed.

Usage
-----
    python cmst_add_aggregation.py --input-dir out/AvV --output-dir out/AvV+U
"""

import argparse
import re
import sys
from pathlib import Path

Z_VAR = re.compile(r"\bz\.(\d+)\.(\d+)\.(\d+)\b")


def detect_n_and_C(lp_path):
    """Infer n and C from the z.i.j.k variables present in an .lp file.

    n is the largest vertex index. C is the largest capacity index on arcs
    leaving the root, which by construction is exactly the vehicle capacity
    (non-root vertices only ever carry up to C-1).
    """
    n = 0
    C = 0
    with open(lp_path, "r") as f:
        for line in f:
            for i, j, k in Z_VAR.findall(line):
                i, j, k = int(i), int(j), int(k)
                n = max(n, i, j)
                if i == 0:
                    C = max(C, k)
    if n == 0 or C == 0:
        raise ValueError(f"{lp_path}: could not infer n and C (no z.i.j.k variables found)")
    return n, C


def find_last_constraint_num(lines):
    """Largest constraint index cN appearing before the Bounds section."""
    last = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Bounds"):
            break
        m = re.match(r"c(\d+)\s*:", stripped)
        if m:
            last = max(last, int(m.group(1)))
    return last


def aggregation_constraints(n, C, start_number):
    """Build the u/w defining constraints, their bounds, and the variable list."""
    upper_limit = {i: C if i == 0 else C - 1 for i in range(n + 1)}
    number = start_number
    constraints, new_vars, bounds = [], [], []

    # u.i.k : total flow of size k leaving vertex i
    for i in range(n + 1):
        for k in range(1, upper_limit[i] + 1):
            line = f"c{number}: - u.{i}.{k}"
            new_vars.append(f"u.{i}.{k}")
            count = 0
            for j in range(n + 1):
                if i == j:
                    continue
                line += f" + z.{i}.{j}.{k}"
                count += 1
            line += " = 0"
            constraints.append(line)
            number += 1
            bounds.append(f" 0 <= u.{i}.{k} <= {count}")

    # w.j.k : total flow of size k entering vertex j
    for j in range(n + 1):
        for k in range(1, C + 1):
            line = f"c{number}: - w.{j}.{k}"
            if k == C and j == 0:
                break  # the root is never entered by a full load
            new_vars.append(f"w.{j}.{k}")
            for i in range(n + 1):
                if i == j:
                    continue
                if k == C:
                    # only the root can send a full load
                    line += f" + z.0.{j}.{k}"
                    break
                line += f" + z.{i}.{j}.{k}"
            line += " = 0"
            constraints.append(line)
            number += 1
            # bounded by 1 because of the in-degree constraints
            bounds.append(f" 0 <= w.{j}.{k} <= 1")

    return constraints, bounds, new_vars, number


def aggregated_flow_constraints(n, C, start_number):
    """Flow conservation rewritten over the aggregated u/w variables."""
    number = start_number
    constraints = []
    for i in range(1, n + 1):
        line = f"c{number}: "
        first = True
        for k in range(1, C + 1):
            if first:
                line += f" w.{i}.{k}" if k == 1 else f" {k} w.{i}.{k}"
                first = False
            else:
                line += f" + {k} w.{i}.{k}"
        for k in range(1, C):
            line += f" - u.{i}.{k}" if k == 1 else f" - {k} u.{i}.{k}"
        line += " = 1"
        constraints.append(line)
        number += 1
    return constraints


def insert_before(lines, keyword, new_lines):
    """Insert new_lines immediately before the first line starting with keyword."""
    idx = next((i for i, l in enumerate(lines) if l.strip().startswith(keyword)), len(lines))
    lines[idx:idx] = new_lines
    return lines


def transform(lp_path, out_path, n=None, C=None):
    if n is None or C is None:
        dn, dC = detect_n_and_C(lp_path)
        n = dn if n is None else n
        C = dC if C is None else C

    lines = open(lp_path, "r").readlines()

    # --- pass 1: u/w defining constraints, bounds, Generals ---
    start = find_last_constraint_num(lines) + 1
    cons, bounds, new_vars, _ = aggregation_constraints(n, C, start)

    lines = insert_before(lines, "Bounds", [c + "\n" for c in cons])

    end_index = next(i for i, l in enumerate(lines) if l.strip().lower() == "end")
    generals = ["Generals\n"]
    for idx, v in enumerate(new_vars):
        generals.append(f" {v} \n" if idx == len(new_vars) - 1 else f" {v} ")
    lines = lines[:end_index] + generals + lines[end_index:]

    lines = insert_before(lines, "Binaries", [b + "\n" for b in bounds])

    # --- pass 2: flow constraints over u/w ---
    start = find_last_constraint_num(lines) + 1
    flow = aggregated_flow_constraints(n, C, start)
    lines = insert_before(lines, "Bounds", [c + "\n" for c in flow])

    out_path.write_text("".join(lines))
    return n, C, len(cons) + len(flow)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-dir", required=True, help="directory of AvV .lp files")
    ap.add_argument("--output-dir", required=True, help="directory to write AvV+U .lp files")
    ap.add_argument("--n", type=int, default=None, help="override inferred n")
    ap.add_argument("--C", type=int, default=None, help="override inferred capacity C")
    args = ap.parse_args()

    in_dir, out_dir = Path(args.input_dir), Path(args.output_dir)
    if not in_dir.is_dir():
        sys.exit(f"error: not a directory: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    lp_files = sorted(in_dir.glob("*.lp"))
    if not lp_files:
        sys.exit(f"error: no .lp files in {in_dir}")

    for lp in lp_files:
        n, C, added = transform(lp, out_dir / lp.name, args.n, args.C)
        print(f"{lp.name}: n={n} C={C} +{added} constraints")

    print(f"\nwrote {len(lp_files)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
