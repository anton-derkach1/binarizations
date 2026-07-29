# CMST code

Code for the Capacitated Minimum Spanning Tree instances in
[`data_instances/CMST/`](../../data_instances/CMST/).

| File | Purpose |
| :--- | :--- |
| `cmst_build_lp.py` | OR-Library `.dat` &rarr; AvV |
| `cmst_add_aggregation.py` | AvV &rarr; AvV+U (adds aggregated `u`, `w` variables) |
| `cmst_make_avv_u_minus_z.py` | AvV+U &rarr; AvV+U-z (deletes the `z`-based flow constraints) |

Python 3, standard library only — no CPLEX, no third-party packages. Each
script reads an input directory and writes to a separate output directory,
leaving its inputs untouched. Pass `-h` to any of them for the full option list.

Unlike the FCT instances, which are generated from scratch, the CMST instances
are **converted** from published data. The pipeline is therefore fully
deterministic: running it on the `.dat` files in
[`data_instances/CMST/source_orlib/`](../../data_instances/CMST/source_orlib/)
reproduces all three committed formulation directories byte for byte.

---

## Full pipeline

```sh
python cmst_build_lp.py \
    --input      ../../data_instances/CMST/source_orlib \
    --output-dir out/AvV

python cmst_add_aggregation.py \
    --input-dir  out/AvV \
    --output-dir out/AvV+U

python cmst_make_avv_u_minus_z.py \
    --input-dir  out/AvV+U \
    --output-dir out/AvV+U-z
```

The three output directories correspond to `allfiles/AvV/`, `allfiles/AvV+U/`
and `allfiles/AvV+U-z/`.

---

## 1. Input format

The scripts read the OR-Library capacitated MST format, as used by the `tc80`
and `te80` test sets:

```
line 1      n C                 n = number of non-root vertices, C = vehicle capacity
remainder   (n+1)*(n+1) ints    the full cost matrix, whitespace separated
```

The cost matrix may be wrapped across any number of lines. Vertex 0 is the
root; all non-root vertices have unit demand. For the paper's instances
$n = 80$ and $C = 5$.

Any file in this format works, so the pipeline can be pointed at other
OR-Library CMST instances without modification.

---

## 2. Building the AvV formulation

`cmst_build_lp.py` writes the capacity-indexed model. Binary variables
$z_{ij}^k$ indicate that arc $(i,j)$ carries flow $k$, for $k = 1 \ldots C$ on
arcs leaving the root and $k = 1 \ldots C-1$ elsewhere:

$$\min \sum_{i,j,k} c_{ij}\, z_{ij}^k$$

subject to, for every non-root vertex $i$,

$$\sum_{j,k} z_{ji}^k = 1, \qquad \sum_{j,k} k\, z_{ji}^k - \sum_{j,k} k\, z_{ij}^k = 1$$

the in-degree and flow conservation constraints respectively. Constraints are
emitted in that order, so for a given $n$:

| Constraints | Meaning |
| :--- | :--- |
| `c1` … `cn` | in-degree |
| `c(n+1)` … `c2n` | flow conservation, in terms of `z` |

Accepts either a single `.dat` file or a directory of them.

---

## 3. Adding the aggregated variables

`cmst_add_aggregation.py` appends two groups of constraints.

**Definitions.** For each vertex and each flow value,

$$u_i^k = \sum_{j \neq i} z_{ij}^k, \qquad w_j^k = \sum_{i \neq j} z_{ij}^k$$

written in the file as `- u.i.k + z.i.j1.k + z.i.j2.k + ... = 0`. Only the root
can dispatch a full load of $C$, so $w_j^C$ reduces to $z_{0j}^C$ and $w_0^C$
does not exist. Each $w_j^k$ is bounded above by 1 by the in-degree
constraints.

**Flow conservation over the aggregated variables.** For each non-root $i$,

$$\sum_k k\, w_i^k - \sum_k k\, u_i^k = 1$$

The original `z`-based constraints are left in place at this stage, so an
AvV+U file states flow conservation twice.

$n$ and $C$ are inferred from the `z.i.j.k` variables in the input file, so no
editing is needed for other instance sizes; `--n` and `--C` override if
required.

---

## 4. Removing the `z`-based flow constraints

`cmst_make_avv_u_minus_z.py` deletes constraints `c(n+1)` … `c2n`, leaving flow
conservation expressed only in the aggregated variables. The range is derived
from $n$ rather than hard-coded; for the paper's instances ($n = 80$) it is
`c81`–`c160`. Use `--n` to override.
