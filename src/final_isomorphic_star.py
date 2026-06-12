import pandas as pd
import networkx as nx
from collections import defaultdict
import os

def find_isomorphic_star(G, hub, n_limit=None):
    """
    Finds a hub and its successors that form a strictly induced star graph.
    Leaves must have NO edges to each other and NO edges back to the hub.
    """
    successors = list(G.successors(hub))
    
    # 1. Filter out back-edges to the hub
    valid_leaves = [n for n in successors if not G.has_edge(n, hub)]
    
    # 2. Extract subgraph of leaves to find an independent set
    S = G.subgraph(valid_leaves)
    
    # Greedy Independent Set
    # We sort by degree within the leaf-subgraph and pick nodes with 0 degree
    independent_leaves = [n for n, d in S.degree() if d == 0]
    
    # If the set is still large, we could do more complex MIS, 
    # but for connectomes, thousands of leaves are often independent.
    
    return independent_leaves

def main():
    trio = ('BANC', 'FAFB', 'MCNS')
    graphs = {}
    print("Step 1: Loading graphs...", flush=True)
    for ds in trio:
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        graphs[ds] = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        print(f"  {ds} loaded.", flush=True)

    # Pick the top hub in each
    hubs = {}
    for ds in trio:
        out_deg = dict(graphs[ds].out_degree())
        hubs[ds] = sorted(out_deg.items(), key=lambda x: x[1], reverse=True)[0][0]
    
    print(f"\nStep 2: Identifying independent leaf sets for hubs: {hubs}", flush=True)
    leaf_sets = {}
    for ds in trio:
        leaf_sets[ds] = find_isomorphic_star(graphs[ds], hubs[ds])
        print(f"  {ds} found {len(leaf_sets[ds])} independent leaves.", flush=True)

    # Step 3: Match leaves
    # In a directed star graph, all leaves are structurally identical and 
    # belong to the same automorphism orbit. Therefore, any bijection 
    # between the leaf sets preserves the adjacency matrix. 
    # We sort by ID to provide a deterministic, row-mapped correspondence.
    matched_mapping = {ds: [hubs[ds]] for ds in trio}
    
    min_k = min(len(leaf_sets[ds]) for ds in trio)
    print(f"\nStep 3: Matching {min_k} leaves via structural bijection...", flush=True)
    
    for ds in trio:
        # Deterministic sort for row mapping
        leaf_sets[ds].sort()
        # Add to mapping
        matched_mapping[ds].extend(leaf_sets[ds][:min_k])

    # Step 4: Final Verification of Induced Isomorphism
    # Since they are independent leaves of a hub, the adjacency matrix 
    # MUST be the same (Hub->Leaf only)
    N = len(matched_mapping[trio[0]])
    print(f"\nFinal Verification: N = {N}")
    
    # Check Row 1 -> all others
    for i in range(1, N):
        for ds in trio:
            h = matched_mapping[ds][0]
            l = matched_mapping[ds][i]
            if not graphs[ds].has_edge(h, l):
                print(f"  ERROR: Edge Hub->Leaf missing in {ds} at row {i}")
                return
                
    # Check for extra internal edges (must be 0)
    for i in range(1, N):
        for j in range(1, N):
            if i == j: continue
            for ds in trio:
                if graphs[ds].has_edge(matched_mapping[ds][i], matched_mapping[ds][j]):
                    print(f"  ERROR: Internal edge Leaf->Leaf found in {ds} between row {i} and {j}")
                    return

    print("  Verification Passed: Strictly Isomorphic Induced Subgraph confirmed.")
    
    os.makedirs("results", exist_ok=True)
    pd.DataFrame(matched_mapping).to_csv("results/submission.csv", index=False)
    print(f"SUCCESS: Result saved with N={N}")

if __name__ == "__main__":
    main()
