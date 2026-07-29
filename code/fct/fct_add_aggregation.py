#!/usr/bin/env python3
"""
Add aggregation variables to the FCT AvV formulation, producing AvV+U.

    fctgen2 -o 2  -->  AvV  --[this script]-->  AvV+U  -->  AvV+U-z

Two groups of constraints are appended to each AvV (z2fct_*.lp) file.

1. Definition of the aggregated variables

       u.i.k  =  sum_j z.i.j.k     over arcs out of supply node i with a_ij >= k
       w.j.k  =  sum_i z.i.j.k     over arcs into demand node j with a_ij >= k

   written in the file as  "- u.i.k + z.i.j1.k + z.i.j2.k + ... = 0".

2. Flow conservation restated in the aggregated variables

       sum_k k*u.i.k <= s_i        for each supply node i
       sum_k k*w.j.k  = d_j        for each demand node j

The original z-based constraints are left untouched; fct_make_avv_u_minus_z.py
removes them.

IMPORTANT: two input directories are required
---------------------------------------------
The arc capacities a_ij = min(s_i, d_j) and the aggregation bound
C = max_ij a_ij cannot be recovered from the binarized file, so the supply and
demand values are read from the corresponding ORIGINAL formulation file
(fct_*.lp, produced by fctgen2 with option 1). Files are paired by the part of
the name after the first underscore, e.g.

    z2fct_40_40_20_095_5__00005.lp   <->   fct_40_40_20_095_5__00005.lp

Usage
-----
    python fct_add_aggregation.py \
        --avv-dir      data_instances/FCTP/allfiles/AvV \
        --original-dir data_instances/FCTP/allfiles/fct \
        --output-dir   out/AvV_plus_U
"""

import argparse
import re
import sys
from pathlib import Path


def parse_filename(filename):
    """Split 'z2fct_40_40_20_095_5__00005.lp' into ('z2fct', '40_40_20_095_5__00005')."""
    parts = filename.rsplit(".lp", 1)[0].split("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def extract_n(filename):
    """First numeric field of the filename, i.e. the number of supply nodes."""
    for part in filename.split("_"):
        if part.isdigit():
            return int(part)
    return None


def extract_capacities(lp_file, n):
    """Read supply then demand right-hand sides from an ORIGINAL fct_*.lp file.

    fctgen2 writes the n supply constraints (<=) first, then the n demand
    constraints (=), so the first n right-hand sides are the supplies s_i and
    the next n are the demands d_j.
    """
    capacities = {}
    count = 0
    seen = 0
    node_type = "s"
    with open(lp_file, "r") as f:
        for line in f:
            if seen >= 2 * n:
                break
            parts = line.split()
            for part in parts:
                if part.startswith("<=") or part.startswith("="):
                    capacities[f"{node_type} {count}"] = int(parts[-1])
                    count += 1
                    seen += 1
                    if count == n:
                        count = 0
                        node_type = "d"
                    break
    if seen < 2 * n:
        raise ValueError(f"{lp_file}: found {seen} capacities, expected {2 * n}")
    return capacities


def get_a_i_j(capacities):
    """Arc capacities a_ij = min(s_i, d_j)."""
    n = len(capacities) // 2
    return [[min(capacities[f"s {i}"], capacities[f"d {j}"]) for j in range(n)]
            for i in range(n)]


def get_C(a):
    """C = max_ij a_ij."""
    return max(max(row) for row in a)


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


def aggregation_constraints(n, C, capacities, a, start_number):
    number = start_number
    constraints, new_vars, bounds = [], [], []

    # u.i.k : flow of size k leaving supply node i
    for i in range(n):
        for k in range(1, C + 1):
            if int(capacities[f"s {i}"]) < k:
                break
            line = f"c{number}: - u.{i}.{k}"
            new_vars.append(f"u.{i}.{k}")
            count = 0
            for j in range(n):
                if int(a[i][j]) >= k:
                    line += f" + z.{i}.{j}.{k}"
                    count += 1
            line += " = 0"
            constraints.append(line)
            number += 1
            bounds.append(f" 0 <= u.{i}.{k} <= {count}")

    # w.j.k : flow of size k entering demand node j
    for j in range(n):
        for k in range(1, C + 1):
            if int(capacities[f"d {j}"]) < k:
                break
            line = f"c{number}: - w.{j}.{k}"
            new_vars.append(f"w.{j}.{k}")
            count = 0
            for i in range(n):
                if int(a[i][j]) >= k:
                    line += f" + z.{i}.{j}.{k}"
                    count += 1
            line += " = 0"
            constraints.append(line)
            number += 1
            bounds.append(f" 0 <= w.{j}.{k} <= {count}")

    return constraints, bounds, new_vars, number


def aggregated_flow_constraints(n, C, capacities, start_number):
    number = start_number
    constraints = []

    for i in range(n):
        line = f"c{number}: "
        first = True
        for k in range(1, C + 1):
            if int(capacities[f"s {i}"]) < k:
                break
            if first:
                line += f" u.{i}.{k}" if k == 1 else f" {k} u.{i}.{k}"
                first = False
            else:
                line += f" + {k} u.{i}.{k}"
        line += f" <= {capacities[f's {i}']}"
        constraints.append(line)
        number += 1

    for j in range(n):
        line = f"c{number}: "
        first = True
        for k in range(1, C + 1):
            if int(capacities[f"d {j}"]) < k:
                break
            if first:
                line += f" w.{j}.{k}" if k == 1 else f" {k} w.{j}.{k}"
                first = False
            else:
                line += f" + {k} w.{j}.{k}"
        line += f" = {capacities[f'd {j}']}"
        constraints.append(line)
        number += 1

    return constraints


def insert_before(lines, keyword, new_lines):
    idx = next((i for i, l in enumerate(lines) if l.strip().startswith(keyword)), len(lines))
    lines[idx:idx] = new_lines
    return lines


def transform(avv_path, original_path, out_path):
    n = extract_n(avv_path.name)
    if n is None:
        raise ValueError(f"{avv_path.name}: could not extract n from filename")

    capacities = extract_capacities(original_path, n)
    a = get_a_i_j(capacities)
    C = get_C(a)

    lines = open(avv_path, "r").readlines()

    start = find_last_constraint_num(lines) + 1
    cons, bounds, new_vars, _ = aggregation_constraints(n, C, capacities, a, start)

    lines = insert_before(lines, "Bounds", [c + "\n" for c in cons])

    end_index = next(i for i, l in enumerate(lines) if l.strip().lower() == "end")
    generals = ["Generals\n"]
    for idx, v in enumerate(new_vars):
        generals.append(f" {v} \n" if idx == len(new_vars) - 1 else f" {v} ")
    lines = lines[:end_index] + generals + lines[end_index:]

    lines = insert_before(lines, "Binaries", [b + "\n" for b in bounds])

    start = find_last_constraint_num(lines) + 1
    flow = aggregated_flow_constraints(n, C, capacities, start)
    lines = insert_before(lines, "Bounds", [c + "\n" for c in flow])

    out_path.write_text("".join(lines))
    return n, C, len(cons) + len(flow)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--avv-dir", required=True, help="directory of AvV files (z2fct_*.lp)")
    ap.add_argument("--original-dir", required=True,
                    help="directory of ORIGINAL formulation files (fct_*.lp), for capacities")
    ap.add_argument("--output-dir", required=True, help="directory to write AvV+U files")
    ap.add_argument("--output-prefix", default="z2fctWithUW",
                    help="filename prefix for outputs (default: z2fctWithUW)")
    args = ap.parse_args()

    avv_dir, orig_dir, out_dir = Path(args.avv_dir), Path(args.original_dir), Path(args.output_dir)
    for d in (avv_dir, orig_dir):
        if not d.is_dir():
            sys.exit(f"error: not a directory: {d}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # index the originals by the identifier following the first underscore
    originals = {}
    for p in orig_dir.glob("*.lp"):
        _, ident = parse_filename(p.name)
        if ident:
            originals[ident] = p

    lp_files = sorted(avv_dir.glob("*.lp"))
    if not lp_files:
        sys.exit(f"error: no .lp files in {avv_dir}")

    done, missing = 0, []
    for lp in lp_files:
        _, ident = parse_filename(lp.name)
        original = originals.get(ident)
        if original is None:
            missing.append(lp.name)
            print(f"{lp.name}: SKIPPED - no matching original for '{ident}'")
            continue
        out_name = f"{args.output_prefix}_{ident}.lp"
        n, C, added = transform(lp, original, out_dir / out_name)
        print(f"{lp.name}: n={n} C={C} +{added} constraints -> {out_name}")
        done += 1

    print(f"\nwrote {done} file(s) to {out_dir}")
    if missing:
        sys.exit(f"error: {len(missing)} file(s) had no matching original: {missing}")


if __name__ == "__main__":
    main()
