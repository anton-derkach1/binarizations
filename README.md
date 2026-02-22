# Binarization Formulations for FCT and CMST

This repository contains the Mathematical Programming (LP) instances and computational results using CPLEX and Gurobi for various binarization formulations applied to two problem classes: the **Fixed Charge Transportation Problem (FCT)** and the **Capacitated Minimum Spanning Tree (CMST)**.

## Problem Classes & Datasets

### Fixed Charge Transportation (FCT)
We use a dataset of **20 randomly generated instances** for the FCT experiments.
* **Network Size:** The number of suppliers and customers are equal ($n$), where $n \in \{30, 40\}$. 
* **Capacities:** Generated using a parameter $B \in \{10, 20\}$, which serves as the ceiling for all capacities.
* **Demand/Supply:** A factor $r=0.95$ is used for the total demand to total supply ratio.
* **Sample Size:** 5 unique instances were generated for each $(n, B)$ combination using the procedure described in AVV2017.

### Capacitated Minimum Spanning Tree (CMST)
We utilize **20 CMST instances from the OR-Library (ORLIB)** for the CMST experiments.
* **Instances:** Specifically the `tc80` and `te80` test sets.
* **Vertices:** $n = 80$ non-root vertices.
* **Demands & Capacity:** All vertices have unitary demands with a vehicle capacity of $C = 5$.

## Formulations Considered
The LP files in this repository correspond to the following formulations:

| Abbreviation | Formulation Description |
| :--- | :--- |
| **FCT** | Standard Fixed Charge Transportation formulation |
| **FullB** | Full Binarization |
| **AvV** | Full Binarization with Strengthening |
| **UnaryB<sup>+</sup>** | Unary Binarization with Strengthening |
| **LogB<sup>+</sup>** | Logarithmic Binarization with Strengthening |
| **AvV-z** | AvV formulation with the flow constraints in terms of binary $z$ variables removed. |
| **AvV+U** | AvV formulation where new general integer variables are introduced to link equally sized flows from all supply (resp. demand) nodes into a single demand (resp. supply) node. |
| **AvV+U-z** | AvV+U formulation with the flow constraints in terms of binary $z$ variables removed. |

The results, including comparisons of LP gaps, node counts, and solution times for these formulations, are documented in the TABLES.md file.
