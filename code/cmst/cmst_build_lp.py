#!/usr/bin/env python3
"""
Build the capacity-indexed (AvV) CMST formulation from an OR-Library .dat file.

Stage 1 of 3 in the CMST pipeline:

    .dat  --[this script]-->  AvV  -->  AvV+U  -->  AvV+U-z

Input format (OR-Library capacitated MST, e.g. tc80-1.dat, te80-1.dat):
    line 1      : n C          n = number of non-root vertices, C = vehicle capacity
    remainder   : (n+1)*(n+1)  integers, the full cost matrix, whitespace separated
                  (may be wrapped across any number of lines)

Vertex 0 is the root. All non-root vertices have unit demand.

Model
-----
Binary variables z.i.j.k indicate that arc (i,j) carries flow k, for
k = 1..C at the root (i = 0) and k = 1..C-1 elsewhere.

    min  sum_{i,j,k} cost[i][j] * z.i.j.k
    s.t. sum_{j,k} z.j.i.k = 1                    for each non-root i   (in-degree)
         sum_{j,k} k*z.j.i.k - sum_{j,k} k*z.i.j.k = 1  for each non-root i  (flow)
         z binary

Usage
-----
    python cmst_build_lp.py --input path/to/dat_dir --output-dir out/AvV
    python cmst_build_lp.py --input tc80-1.dat      --output-dir out/AvV
"""

import argparse
import os
import sys
from pathlib import Path


def read_cmst_dat_file(filepath):
    """Parse an OR-Library CMST .dat file into (n, C, cost_matrix).

    cost_matrix is a list of (n+1) rows of (n+1) ints.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    n, C = map(int, lines[0].strip().split())
    size = n + 1

    values = []
    for line in lines[1:]:
        values.extend(map(int, line.strip().split()))

    expected = size * size
    if len(values) != expected:
        raise ValueError(
            f"{filepath}: expected {expected} cost values for n={n}, found {len(values)}"
        )

    cost = [values[r * size:(r + 1) * size] for r in range(size)]
    return n, C, cost


def build_lp_text(n, C, cost):
    """Return the full .lp file contents for the AvV (capacity-indexed) model."""
    # Arcs leaving the root may carry up to C units; all others up to C-1.
    upper_limit = {i: C if i == 0 else C - 1 for i in range(n + 1)}

    # ---- objective, and the binary variable list in the same order ----
    obj = " obj: "
    variables = []
    first = True
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                continue
            for k in range(1, upper_limit[i] + 1):
                term = f"{cost[i][j]} z.{i}.{j}.{k}"
                obj += term if first else f" + {term}"
                first = False
                variables.append(f"z.{i}.{j}.{k}")

    constraints = []
    counter = 1

    # ---- in-degree: every non-root vertex is entered exactly once ----
    for i in range(1, n + 1):
        line = f" c{counter}: "
        first = True
        for j in range(n + 1):
            if i == j:
                continue
            for k in range(1, upper_limit[j] + 1):
                term = f"z.{j}.{i}.{k}"
                line += term if first else f" + {term}"
                first = False
        line += " = 1"
        constraints.append(line)
        counter += 1

    # ---- flow: inflow minus outflow equals the unit demand at i ----
    for i in range(1, n + 1):
        line = f" c{counter}: "
        first = True
        for j in range(n + 1):
            if i == j:
                continue
            for k in range(1, upper_limit[j] + 1):
                term = f"z.{j}.{i}.{k}" if k == 1 else f"{k} z.{j}.{i}.{k}"
                line += term if first else f" + {term}"
                first = False
            for k in range(1, C):
                line += f" - z.{i}.{j}.{k}" if k == 1 else f" - {k} z.{i}.{j}.{k}"
        line += " = 1"
        constraints.append(line)
        counter += 1

    bounds = []
    for i in range(n + 1):
        for j in range(n + 1):
            if i == j:
                continue
            for k in range(1, upper_limit[i] + 1):
                bounds.append(f" 0 <= z.{i}.{j}.{k} <= 1")

    out = ["Minimize\n", f"{obj}\n", "Subject To\n"]
    out += [f"{c}\n" for c in constraints]
    if bounds:
        out.append("Bounds\n")
        out += [f"{b}\n" for b in bounds]
    if variables:
        out.append("Binaries\n")
        out += [f" {v} " for v in variables]
    out.append("\nEnd\n")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True,
                    help="a .dat file, or a directory containing .dat files")
    ap.add_argument("--output-dir", required=True,
                    help="directory to write .lp files into (created if absent)")
    args = ap.parse_args()

    src = Path(args.input)
    if src.is_dir():
        dat_files = sorted(p for p in src.iterdir() if p.suffix.lower() == ".dat")
    elif src.is_file():
        dat_files = [src]
    else:
        sys.exit(f"error: no such file or directory: {src}")

    if not dat_files:
        sys.exit(f"error: no .dat files found in {src}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for dat in dat_files:
        n, C, cost = read_cmst_dat_file(dat)
        target = out_dir / (dat.stem + ".lp")
        target.write_text(build_lp_text(n, C, cost))
        print(f"{dat.name}: n={n} C={C} -> {target}")

    print(f"\nwrote {len(dat_files)} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
