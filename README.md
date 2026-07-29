# Binarization Formulations for FCT and CMST

This repository contains the Mathematical Programming (LP) instances, the code
that produces them, and the computational results using CPLEX and Gurobi for
various binarization formulations applied to two problem classes: the
**Fixed Charge Transportation Problem (FCT)** and the **Capacitated Minimum
Spanning Tree (CMST)**.

Results — LP gaps, node counts and solution times — are in
[TABLES.md](./TABLES.md).

## Repository layout

```
code/
├── fct/          instance generator (C++/CPLEX) and post-processing scripts
└── cmst/         .dat to .lp conversion and post-processing scripts
data_instances/
├── FCTP/
│   ├── allfiles/               10 formulations x 20 instances
│   └── formulation_cuts_added/ the same instances with formulation cuts added
└── CMST/
    ├── source_orlib/           the original OR-Library .dat files
    ├── allfiles/               3 formulations x 10 instances
    └── formulation_cuts_added/ the same instances with formulation cuts added
TABLES.md         computational results
```

Each code directory has its own README with build and usage instructions:
[`code/fct/README.md`](./code/fct/README.md) and
[`code/cmst/README.md`](./code/cmst/README.md).

## Problem Classes & Datasets

### Fixed Charge Transportation (FCT)

We use a dataset of **20 randomly generated instances** for the FCT experiments.

* **Network Size:** The number of suppliers and customers are equal ($n$), where $n \in \{30, 40\}$.
* **Capacities:** Generated using a parameter $B \in \{10, 20\}$, which serves as the ceiling for all capacities.
* **Demand/Supply:** A factor $r=0.95$ is used for the total demand to total supply ratio.
* **Sample Size:** 5 unique instances were generated for each $(n, B)$ combination using the procedure described in AVV2017.

The instances are produced by `code/fct/fctgen2.cpp`, which also writes most of
the formulations directly.

### Capacitated Minimum Spanning Tree (CMST)

We utilize **10 CMST instances from the OR-Library (ORLIB)** for the CMST experiments.

* **Instances:** 5 instances from each of the `tc80` and `te80` test sets.
* **Vertices:** $n = 80$ non-root vertices.
* **Demands & Capacity:** All vertices have unitary demands with a vehicle capacity of $C = 5$.

The original OR-Library data files are included in
`data_instances/CMST/source_orlib/`, and `code/cmst/cmst_build_lp.py` converts
them into the formulations used here.

## Formulations Considered

The LP files in this repository correspond to the following formulations.

| Abbreviation | Formulation Description | FCT directory | CMST directory |
| :--- | :--- | :--- | :--- |
| **FCT** | Standard Fixed Charge Transportation formulation | `fct/` | — |
| **FullB** | Full Binarization | `Full/` | — |
| **AvV** | Full Binarization with Strengthening | `AvV/` | `AvV/` |
| **UnaryB** | Unary Binarization | `Unary/` | — |
| **UnaryB<sup>+</sup>** | Unary Binarization with Strengthening | `Unary_strengthening/` | — |
| **LogB** | Logarithmic Binarization | `Logarithmic/` | — |
| **LogB<sup>+</sup>** | Logarithmic Binarization with Strengthening | `Logarithmic_strengthening/` | — |
| **AvV-z** | AvV formulation with the flow constraints in terms of binary $z$ variables removed. | `AvV-z/` | — |
| **AvV+U** | AvV formulation where new general integer variables are introduced to link equally sized flows from all supply (resp. demand) nodes into a single demand (resp. supply) node. | `AvV_plus_U/` | `AvV+U/` |
| **AvV+U-z** | AvV+U formulation with the flow constraints in terms of binary $z$ variables removed. | `AvV_plus_U_minus_z/` | `AvV+U-z/` |

Directories are relative to `data_instances/FCTP/allfiles/` and
`data_instances/CMST/allfiles/` respectively. FCT covers all ten formulations;
CMST covers AvV, AvV+U and AvV+U-z.

### How each formulation is produced

For FCT, `fctgen2` writes FCT, FullB, AvV, UnaryB, UnaryB<sup>+</sup>, LogB and
LogB<sup>+</sup> directly, selected by its `probtype` argument. The three
remaining formulations are derived from AvV by the Python scripts in
`code/fct/`. For CMST, `cmst_build_lp.py` writes AvV from the OR-Library data
and the other two are derived from it. See the per-directory READMEs for the
exact commands.

## Data organization

Both problem classes use the same two-directory scheme:

* **`allfiles/`** — the instances as generated, one subdirectory per formulation.
* **`formulation_cuts_added/`** — instances with the formulation cuts discussed
  in the paper added to the model, in subdirectories named
  `<formulation>_formulation_cuts/`.

Not every formulation has a cuts counterpart: for FCT these are AvV, AvV-z,
AvV+U, FullB, UnaryB, UnaryB<sup>+</sup>, LogB and LogB<sup>+</sup>, and for CMST
AvV, AvV+U and AvV+U-z. FCT additionally has `Full_binarization_GMI/`, the
FullB instances with Gomory mixed-integer cuts added, and
`Full_binarization_GMI_formulation_cuts/`, with both.

## Reproducibility

The `.lp` files committed here are the exact instances used for the results in
[TABLES.md](./TABLES.md), and are the authoritative artifacts.

The two classes differ in how far they can be regenerated:

* **CMST is fully deterministic.** The instances are converted from published
  OR-Library data, which is included in this repository. Running the pipeline
  in `code/cmst/` reproduces every committed CMST `.lp` file byte for byte, and
  the same scripts work on any other OR-Library CMST instance.
* **FCT instances are randomly generated.** Rerunning `fctgen2` produces valid
  instances of the same classes, but not bit-for-bit copies of the committed
  files, since the data depends on the platform's `rand()`. The
  post-processing scripts in `code/fct/` are deterministic and do reproduce
  `AvV-z/`, `AvV+U/` and `AvV+U-z/` byte for byte from the committed `AvV/` and
  `fct/` directories.
