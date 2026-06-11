import pandas as pd
import networkx as nx
import numpy as np
from itertools import combinations
import json

def find_hub_motifs():
    datasets = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    graphs = {}
    top_hubs = {}
    
    for ds in datasets:
        print(f"Loading {ds}...")
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        G = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        graphs[ds] = G
        
        # Get top 50 hubs by out-degree
        out_deg = dict(G.out_degree())
        sorted_nodes = sorted(out_deg.items(), key=lambda x: x[1], reverse=True)[:50]
        top_hubs[ds] = [n for n, d in sorted_nodes]

    # Try all trios of datasets
    for trio in combinations(datasets, 3):
        print(f"Checking trio {trio} for hub-to-hub isomorphism...")
        
        # We'll try to match hubs by their out-degree rank
        # i.e., Rank 1 in BANC matches Rank 1 in FAFB, etc.
        
        # Try different sizes of hub-sets
        for n_hubs in range(20, 2, -1):
            hubs_in_trio = {ds: top_hubs[ds][:n_hubs] for ds in trio}
            
            adj_matrices = {}
            for ds in trio:
                nodes = hubs_in_trio[ds]
                G_sub = graphs[ds].subgraph(nodes)
                adj = nx.to_numpy_array(G_sub, nodelist=nodes)
                adj_matrices[ds] = adj
            
            ref_adj = adj_matrices[trio[0]]
            if all((adj_matrices[ds] == ref_adj).all() for ds in trio[1:]):
                print(f"SUCCESS: Found isomorphic hub-motif of size {n_hubs} in {trio}")
                
                report_data = {
                    "trio": list(trio),
                    "nodes": hubs_in_trio,
                    "adj": ref_adj.tolist()
                }
                with open("results/motif_data.json", "w") as f:
                    json.dump(report_data, f)
                return

if __name__ == "__main__":
    find_hub_motifs()
