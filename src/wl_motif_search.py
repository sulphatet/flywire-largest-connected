import pandas as pd
import networkx as nx
import hashlib
from collections import Counter, defaultdict
import json

def get_wl_hash(G, node, labels):
    preds = sorted(labels[p] for p in G.predecessors(node))
    succs = sorted(labels[s] for s in G.successors(node))
    signature = (labels[node], tuple(preds), tuple(succs))
    return hashlib.md5(str(signature).encode()).hexdigest()

def find_isomorphic_motifs():
    datasets = ["BANC", "FAFB", "MANC", "MAOL", "MCNS"]
    graphs = {}
    
    for ds in datasets:
        print(f"Loading {ds}...")
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        graphs[ds] = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())

    # Step 1: Initial labels (Degree signatures)
    node_labels = {}
    for ds, G in graphs.items():
        node_labels[ds] = {n: (G.in_degree(n), G.out_degree(n)) for n in G.nodes()}

    # Step 2: 1 Round of WL hashing (Degrees + Neighbor Degrees)
    print(f"WL Round 1...")
    wl1_labels = {}
    for ds, G in graphs.items():
        wl1_labels[ds] = {n: get_wl_hash(G, n, node_labels[ds]) for n in G.nodes()}

    # Step 3: Find shared hashes
    hash_to_nodes = defaultdict(lambda: defaultdict(list))
    for ds, labels in wl1_labels.items():
        for node, h in labels.items():
            hash_to_nodes[h][ds].append(node)

    # Filter hashes present in at least 3 datasets and unique in each
    shared_unique_anchors = []
    for h, dss in hash_to_nodes.items():
        if len(dss) >= 3 and all(len(nodes) == 1 for nodes in dss.values()):
            shared_unique_anchors.append({ds: nodes[0] for ds, nodes in dss.items()})

    print(f"Found {len(shared_unique_anchors)} unique anchor neurons with 1-round WL.")

    # Step 4: Greedy Search for interconnected anchors
    # We want a set of anchors that share the same 3 datasets and have identical edge patterns
    
    # Group anchors by the trio of datasets they belong to
    trio_groups = defaultdict(list)
    for anchor in shared_unique_anchors:
        trio = tuple(sorted(anchor.keys()))
        if len(trio) >= 3:
            for combo in combinations(trio, 3):
                trio_groups[combo].append({ds: anchor[ds] for ds in combo})

    for trio, anchors in trio_groups.items():
        if len(anchors) < 3:
            continue
            
        print(f"Checking trio {trio} with {len(anchors)} shared anchors...")
        
        # We'll use a simple greedy approach: 
        # Start with all anchors, and iteratively remove nodes that violate isomorphism
        # until we have a perfectly isomorphic subset.
        
        current_anchors = anchors
        
        while len(current_anchors) >= 3:
            n = len(current_anchors)
            adj_matrices = {}
            for ds in trio:
                nodes = [a[ds] for a in current_anchors]
                G_sub = graphs[ds].subgraph(nodes)
                adj = nx.to_numpy_array(G_sub, nodelist=nodes)
                adj_matrices[ds] = adj
            
            # Check if all matrices match
            ref_adj = adj_matrices[trio[0]]
            mismatches = []
            for ds in trio[1:]:
                if not (adj_matrices[ds] == ref_adj).all():
                    # Find which node indices cause the mismatch
                    diff = (adj_matrices[ds] != ref_adj)
                    rows, cols = diff.nonzero()
                    mismatches.extend(rows)
                    mismatches.extend(cols)
            
            if not mismatches:
                # Found a perfectly isomorphic subset!
                print(f"SUCCESS: Found isomorphic motif of size {n} in {trio}")
                
                # Save results
                selected_nodes = {ds: [a[ds] for a in current_anchors] for ds in trio}
                report_data = {
                    "trio": list(trio),
                    "nodes": selected_nodes,
                    "adj": ref_adj.tolist()
                }
                with open("results/motif_data.json", "w") as f:
                    json.dump(report_data, f)
                return
            
            # Remove the node that appears most frequently in mismatches
            most_common_mismatch = Counter(mismatches).most_common(1)[0][0]
            current_anchors = [a for i, a in enumerate(current_anchors) if i != most_common_mismatch]

    print("No complex isomorphic motif found even with 1-round WL anchors.")

if __name__ == "__main__":
    from itertools import combinations
    find_isomorphic_motifs()
