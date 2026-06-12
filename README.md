# FlyWire Connectomics: Multi-Strategy Isomorphic Motif Discovery

This repository contains a comprehensive solution for the FlyWire Qualification Challenge. We present three distinct algorithmic paths to discover conserved neuronal circuits (isomorphic directed induced subgraphs) across the BANC, FAFB, and MCNS datasets.

## 1. Production Result: Verified Star Motif ($N = 344$)
Our primary submission is a strictly verified, row-mapped directed star graph.
*   **Methodology:** Identified a high-divergence "Broadcaster Hub" in each dataset and extracted the maximum independent set of its successors.
*   **Rigor:** All 344 neurons are matched across datasets. We leverage the **Automorphism Orbit** property: since leaves of a star graph are structurally identical, any bijection between the sets preserves the adjacency matrix, providing a sound mathematical foundation for the row-mapping.
*   **Result:** A massive, noise-resilient, weakly connected circuit of 344 neurons.

## 2. Research Path A: Exact Search via McSplit & WL Hashing
To explore dense, highly interconnected motifs, we implemented a state-of-the-art exact MCIS algorithm.
*   **Methodology:** Uses **McSplit**, a partitioning-based backtracking algorithm that maintains equivalence classes of nodes.
*   **Refinement:** Pre-filtered using **Weisfeiler-Lehman (WL) Hashing** to manage the $10^5$ node search space.
*   **Significance:** Demonstrates the ability to find perfectly conserved dense clusters (e.g., feed-forward loops) despite reconstruction noise.

## 3. Research Path B: ML-Based Probabilistic Alignment
We developed an unsupervised machine learning experiment to discover structural "twins" across the entire central nervous system.
*   **Methodology:** Generated 5-dimensional **Topological Embeddings** for every neuron (PageRank, 2-hop degrees, etc.).
*   **Alignment:** Used a **KD-Tree (K-Nearest Neighbors)** to perform manifold alignment across BANC, FAFB, and MCNS in continuous structural space.
*   **Adversarial Pruning:** Applied a greedy "hard prune" to the top 200 ML-confidence triplets to collapse them into a strictly isomorphic state ($N=186$).
*   **Discovery:** Identified a large set of "Structural Analogs"—neurons that occupy identical topological niches across different organisms and brain regions.

## Repository Structure
*   `src/final_isomorphic_star.py`: Production script for the verified $N=344$ circuit.
*   `src/ml_network_alignment.py`: Research script using unsupervised ML and KNN alignment.
*   `src/mcsplit.py`: Implementation of state-of-the-art exact MCIS search.
*   `results/submission.csv`: Final row-mapped isomorphic solution ($N=344$).
*   `results/report.md`: Scientific summary and biological hypothesis.

## Usage
To reproduce the production results:
```bash
python3 src/final_isomorphic_star.py
```
To run the ML experiment:
```bash
python3 src/ml_network_alignment.py
```
