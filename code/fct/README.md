# FCT code

Code for the Fixed Charge Transportation instances in
[`data_instances/FCTP/`](../../data_instances/FCTP/).

| File | Purpose |
| :--- | :--- |
| `fctgen2.cpp`, `makefile` | instance generator; writes a chosen formulation directly to `.lp` |
| `fct_add_aggregation.py` | AvV &rarr; AvV+U (adds aggregated `u`, `w` variables) |
| `fct_make_avv_minus_z.py` | AvV &rarr; AvV-z (rewrites flow constraints over `x`) |
| `fct_make_avv_u_minus_z.py` | AvV+U &rarr; AvV+U-z (deletes the `z`-based flow constraints) |

The generator produces seven of the ten formulations directly. The remaining
three (AvV-z, AvV+U, AvV+U-z) are obtained by post-processing its output with
the Python scripts.

---

## 1. Generator

### Requirements

* **IBM ILOG CPLEX 22.1** — the generator builds each model through the CPLEX
  callable library and uses `CPXwriteprob` to write the `.lp` files. A CPLEX
  installation and licence are required to compile and run it.
* `g++` and `make`.

### Building

The `makefile` refers to a CPLEX installation through two relative paths:

```make
CPX_INC = -I../IBM/ILOG/CPLEX_Studio221/cplex/include/ilcplex/
CPX_LIB = -L../IBM/ILOG/CPLEX_Studio221/cplex/lib/x86-64_linux/static_pic -lcplex -lm -lpthread
```

**Edit both to match your own CPLEX installation** before building; they will
not be correct as shipped. Note that `CPX_INC` points at the `ilcplex`
directory itself, because the source includes `<cplex.h>` rather than
`<ilcplex/cplex.h>`. Then:

```sh
make fctgen2      # produces fctgen2.exe
```

### Running

```
fctgen2 n m modulo factor r [seed>0] [probtype=1..10] [xtype=0/1]
```

| Argument | Meaning |
| :--- | :--- |
| `n`, `m` | number of supply and demand nodes |
| `modulo` | ceiling used when drawing capacities (called $B$ in the paper) |
| `factor` | ratio of total demand to total supply |
| `r` | number of instances to generate |
| `seed` | random seed; instance *i* uses `seed + i` |
| `probtype` | which formulation to write (see below) |
| `xtype` | `0` = continuous `x`, `1` = integer `x` |

Files are written to the current working directory. Running `fctgen2` with no
arguments prints the same usage summary.

### Formulations

`probtype` selects the formulation. The seven values used for the paper:

| `probtype` | Paper name | Output prefix | Directory |
| :--- | :--- | :--- | :--- |
| 1 | FCT | `fct_` | `allfiles/fct/` |
| 2 | AvV | `z2fct_` | `allfiles/AvV/` |
| 3 | FullB | `z3fct_` | `allfiles/Full/` |
| 4 | UnaryB | `z4fct_` | `allfiles/Unary/` |
| 5 | UnaryB<sup>+</sup> | `z5fct_` | `allfiles/Unary_strengthening/` |
| 7 | LogB | `z7fct_` | `allfiles/Logarithmic/` |
| 10 | LogB<sup>+</sup> | `z10fct_` | `allfiles/Logarithmic_strengthening/` |

The generator also accepts `probtype` 6, 8 and 9, which are not used in the
paper. **Note that LogB<sup>+</sup> is `probtype = 10`, not 8.** Option 8 adds
only the strengthening constraints, whereas option 10 adds both the
strengthening constraints and the additional constraints that tighten the
logarithmic expansion when an arc capacity is not a power of two. Option 6 is
marked in the source as not to be used without understanding what it does.

Output filenames follow

```
fct_<n>_<m>_<modulo>_<100*factor>_<r>__<seed+i>.lp              (probtype 1)
z<probtype>fct_<n>_<m>_<modulo>_<100*factor>_<r>__<seed+i>.lp   (otherwise)
```

### Reproducing the paper's instance set

Twenty instances: $n = m \in \{30, 40\}$, $B \in \{10, 20\}$, ratio $0.95$,
five instances per combination, seed 1.

```sh
for opt in 1 2 3 4 5 7 10; do
  ./fctgen2.exe 30 30 10 .95 5 1 $opt
  ./fctgen2.exe 30 30 20 .95 5 1 $opt
  ./fctgen2.exe 40 40 10 .95 5 1 $opt
  ./fctgen2.exe 40 40 20 .95 5 1 $opt
done
```

> **On reproducibility.** The generator draws instance data pseudo-randomly.
> Rerunning these commands produces valid instances of the same classes, but
> not bit-for-bit copies of the files in `data_instances/`, which depend on the
> platform's `rand()`. The committed `.lp` files are the instances used for the
> results in the paper; treat them, not a regenerated set, as authoritative.

---

## 2. Post-processing scripts

Python 3, standard library only. Every script takes an input directory and
writes to a separate output directory, leaving its inputs untouched. Pass
`-h` to any of them for the full option list.

### AvV &rarr; AvV+U

Adds the aggregated variables

$$u_i^k = \sum_j z_{ij}^k, \qquad w_j^k = \sum_i z_{ij}^k$$

together with flow conservation restated over them.

```sh
python fct_add_aggregation.py \
    --avv-dir      ../../data_instances/FCTP/allfiles/AvV \
    --original-dir ../../data_instances/FCTP/allfiles/fct \
    --output-dir   out/AvV_plus_U
```

**Two input directories are required.** The arc capacities
$a_{ij} = \min(s_i, d_j)$ and the bound $C = \max_{ij} a_{ij}$ cannot be
recovered from a binarized file, so the supply and demand values are read from
the corresponding original-formulation file. Files are paired by the portion of
the name after the first underscore, so `z2fct_40_40_20_095_5__00005.lp` is
matched with `fct_40_40_20_095_5__00005.lp`.

### AvV &rarr; AvV-z

```sh
python fct_make_avv_minus_z.py \
    --input-dir  ../../data_instances/FCTP/allfiles/AvV \
    --output-dir out/AvV-z
```

The generator states flow conservation over the binary `z` variables only. This
script **replaces** those constraints with the equivalent constraints over the
`x` variables, preserving each constraint's number and right-hand side:

```
c2701: z.0.0.1 + 2 z.0.0.2 + ... <= 27        becomes
c2701: x.0.0 + x.0.1 + ... + x.0.29 <= 27
```

### AvV+U &rarr; AvV+U-z

```sh
python fct_make_avv_u_minus_z.py \
    --input-dir  ../../data_instances/FCTP/allfiles/AvV_plus_U \
    --output-dir out/AvV_plus_U_minus_z
```

Here the `z`-based flow constraints are **deleted** rather than rewritten,
because the aggregated `u`/`w` constraints already enforce flow conservation.

### How the target constraints are located

`fctgen2` emits $3n^2$ constraints defining the binarization, followed by the
$2n$ flow constraints ($n$ supply, then $n$ demand). Both `-z` scripts
therefore act on

$$c_{3n^2+1} \;\ldots\; c_{3n^2+2n}$$

with $n$ read from the filename. This gives `c2701`–`c2760` for $n = 30$ and
`c4801`–`c4880` for $n = 40$. Use `--n`, `--start-id` and `--end-id` to
override if you change the generator's constraint order.

Running the three scripts on the committed `AvV/` and `fct/` directories
reproduces `AvV_plus_U/`, `AvV-z/` and `AvV_plus_U_minus_z/` byte for byte.

---

## Original generator notes

Supplied with `fctgen2.cpp` by its author, reproduced verbatim.

> To compile, type 'make fctgen2'
>
> It creates 'fctgen2.exe'. Running ./fctgen2.exe without arguments gives the list of desired arguments.
>
> To create the 5 instances of type (40,20) with the original formulation considered in the paper, type:
>
> ./fctgen2.exe 40 40 20 .95 5 1 1
>
> Here n = 40, m = 40, the modulus is 20, .95 is the ratio of demand to supply, the next 5 says to generate 5 instances, the next 1 is the random seed, the final 1 says to generate the formulation in the original space.
> The most common use of the code would be to try out different formulations by varying the last argument (from 1,2,...,9).
> The next way to vary the instances would be to change the size (n, m).
> The next would be to change the modulus or ratio of demand to supply.
> Finally, one can generate more instances from a class or change the random seed.
>
> As output for the invocation above, the code produces 5 randomly generated files, and also prints to the screen the exact data used per file (the demand and supply values per node plus arc capacities and all costs.
