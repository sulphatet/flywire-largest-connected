import pandas as pd
import networkx as nx
from pathlib import Path
from itertools import combinations
import numpy as np

def find_large_star_graph(G, top_k=100):
    """
    Finds a hub and its Maximum Independent Set of successors.
    A star graph with K leaves has N = K + 1 nodes.
    """
    # 1. Sort nodes by out-degree
    out_degrees = dict(G.out_degree())
    sorted_hubs = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    best_star = {
        "hub": None,
        "leaves": [],
        "size": 0
    }
    
    for hub, deg in sorted_hubs:
        # Get successors
        successors = list(G.successors(hub))
        if not successors:
            continue
            
        # Extract induced subgraph among {hub} + successors
        all_nodes = [hub] + successors
        S = G.subgraph(all_nodes)
        
        # We want a subset of successors (leaves) such that:
        # 1. Hub -> Leaf exists for all leaves (guaranteed by successors)
        # 2. Leaf -> Hub does NOT exist
        # 3. Leaf -> Leaf does NOT exist
        
        valid_leaves = []
        for leaf in successors:
            # Check Leaf -> Hub
            if S.has_edge(leaf, hub):
                continue
            # We'll check Leaf -> Leaf later by finding an independent set
            valid_leaves.append(leaf)
            
        if not valid_leaves:
            continue
            
        # Find independent set among valid leaves
        S_leaves = G.subgraph(valid_leaves)
        # Simple greedy independent set:
        # Nodes with 0 degree in S_leaves are best
        independent_nodes = [n for n, d in S_leaves.degree() if d == 0]
        
        # If we still have nodes with edges, we could do a more complex MIS
        # but let's see if this is enough.
        
        current_size = len(independent_nodes) + 1
        if current_size > best_star["size"]:
            best_star = {
                "hub": hub,
                "leaves": independent_nodes,
                "size": current_size
            }
            
    return best_star

def run_heuristic():
    data_dir = Path("data")
    datasets = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    
    stars = {}
    
    for ds in datasets:
        print(f"Processing {ds} for star graphs...")
        df = pd.read_csv(f"{ds}.csv")
        # Ensure column names are standard
        df.columns = ["source", "target"]
        G = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        
        star = find_large_star_graph(G)
        stars[ds] = star
        print(f"  {ds} found star of size {star['size']}")

    # Find the best combination of 3 datasets
    best_trio = None
    max_min_n = 0
    
    for trio in combinations(datasets, 3):
        min_n = min(stars[d]["size"] for d in trio)
        if min_n > max_min_n:
            max_min_n = min_n
            best_trio = trio
            
    print(f"\nBest Trio: {best_trio} with N = {max_min_n}")
    
    # Generate submission CSV
    if best_trio:
        submission_rows = []
        # Row 1: The Hubs
        hub_row = {d: stars[d]["hub"] for d in best_trio}
        submission_rows.append(hub_row)
        
        # Rows 2 to N: The Leaves
        for i in range(max_min_n - 1):
            leaf_row = {d: stars[d]["leaves"][i] for d in best_trio}
            submission_rows.append(leaf_row)
            
        submission_df = pd.DataFrame(submission_rows)
        submission_df.to_csv("results/submission.csv", index=False)
        print(f"Submission saved to results/submission.csv with {len(submission_df)} rows.")

if __name__ == "__main__":
    run_heuristic()
