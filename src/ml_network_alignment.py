import pandas as pd
import networkx as nx
import numpy as np
from scipy.spatial import KDTree
import os

def extract_advanced_features(G):
    """
    Extracts high-dimensional structural context features.
    Characterizes nodes by their 'social' role and local neighborhood density.
    """
    nodes = list(G.nodes())
    N = len(nodes)
    node_to_idx = {n: i for i, n in enumerate(nodes)}
    
    print("    Computing K-Core, Clustering, and PageRank...", flush=True)
    kcore = nx.core_number(G)
    clustering = nx.clustering(G.to_undirected()) # Local neighborhood density
    pr = nx.pagerank(G, alpha=0.85, tol=1e-3)
    
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    
    features = np.zeros((N, 6))
    
    for i, n in enumerate(nodes):
        features[i, 0] = in_deg[n]
        features[i, 1] = out_deg[n]
        features[i, 2] = kcore[n]
        features[i, 3] = clustering[n]
        features[i, 4] = pr[n]
        # Average neighbor PageRank (who you know)
        preds = list(G.predecessors(n))
        features[i, 5] = np.mean([pr[p] for p in preds]) if preds else 0
        
    # Normalization
    std = np.std(features, axis=0)
    std[std == 0] = 1
    features = (features - np.mean(features, axis=0)) / std
    
    return nodes, node_to_idx, features

def main():
    trio = ('BANC', 'FAFB', 'MCNS')
    graphs = {}
    embeddings = {}
    node_lists = {}
    
    print("Step 1: Extracting Advanced Structural Context (10D Embeddings)...", flush=True)
    for ds in trio:
        print(f"  Processing {ds}...", flush=True)
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        G = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        G.remove_edges_from(nx.selfloop_edges(G))
        graphs[ds] = G
        
        nodes, _, feats = extract_advanced_features(G)
        node_lists[ds] = nodes
        embeddings[ds] = feats

    print("\nStep 2: Seed-and-Grow Manifold Alignment...", flush=True)
    # Find the single most structurally unique node to serve as a seed
    tree_banc = KDTree(embeddings['BANC'])
    tree_mcns = KDTree(embeddings['MCNS'])
    dist_banc, idx_banc = tree_banc.query(embeddings['FAFB'], k=1)
    dist_mcns, idx_mcns = tree_mcns.query(embeddings['FAFB'], k=1)
    
    total_dist = dist_banc + dist_mcns
    seed_fafb_idx = np.argmin(total_dist)
    
    # Initialize weakly connected motif
    current_mapping = {
        'FAFB': [node_lists['FAFB'][seed_fafb_idx]],
        'BANC': [node_lists['BANC'][idx_banc[seed_fafb_idx]]],
        'MCNS': [node_lists['MCNS'][idx_mcns[seed_fafb_idx]]]
    }
    
    used_fafb = {current_mapping['FAFB'][0]}
    used_banc = {current_mapping['BANC'][0]}
    used_mcns = {current_mapping['MCNS'][0]}

    # Expansion Pool: neighbors of matched nodes
    print("  Growing weakly connected ML motif...", flush=True)
    
    for _ in range(200): # Attempt to grow up to N=200
        # Get candidate pool from neighbors of CURRENT motif to ensure weak connectivity
        # We query the KD-Tree only for neighbors of existing nodes
        neighbors_fafb = set()
        for node in current_mapping['FAFB']:
            neighbors_fafb.update(graphs['FAFB'].predecessors(node))
            neighbors_fafb.update(graphs['FAFB'].successors(node))
        
        candidates = list(neighbors_fafb - used_fafb)
        if not candidates: break
            
        # Extract features for FAFB candidates
        fafb_node_to_idx = {n: i for i, n in enumerate(node_lists['FAFB'])}
        cand_idx = [fafb_node_to_idx[c] for c in candidates]
        cand_feats = embeddings['FAFB'][cand_idx]
        
        # Query closest in structural space
        d_b, i_b = tree_banc.query(cand_feats, k=1)
        d_m, i_m = tree_mcns.query(cand_feats, k=1)
        
        # Best candidate is the one with lowest total distance
        total_d = d_b + d_m
        best_cand_local_idx = np.argmin(total_d)
        
        fafb_node = candidates[best_cand_local_idx]
        banc_node = node_lists['BANC'][i_b[best_cand_local_idx]]
        mcns_node = node_lists['MCNS'][i_m[best_cand_local_idx]]
        
        if banc_node not in used_banc and mcns_node not in used_mcns:
            current_mapping['FAFB'].append(fafb_node)
            current_mapping['BANC'].append(banc_node)
            current_mapping['MCNS'].append(mcns_node)
            used_fafb.add(fafb_node)
            used_banc.add(banc_node)
            used_mcns.add(mcns_node)
        else:
            # If best match is used, remove this FAFB node from candidates and retry
            used_fafb.add(fafb_node)

    # Step 3: Strictly Prune to Isomorphism
    print("\nStep 3: Adversarial Pruning for Strict Isomorphism...", flush=True)
    current_indices = list(range(len(current_mapping['FAFB'])))
    while current_indices:
        nodes_b = [current_mapping['BANC'][i] for i in current_indices]
        nodes_f = [current_mapping['FAFB'][i] for i in current_indices]
        nodes_m = [current_mapping['MCNS'][i] for i in current_indices]
        
        adj_b = nx.to_numpy_array(graphs['BANC'].subgraph(nodes_b), nodelist=nodes_b)
        adj_f = nx.to_numpy_array(graphs['FAFB'].subgraph(nodes_f), nodelist=nodes_f)
        adj_m = nx.to_numpy_array(graphs['MCNS'].subgraph(nodes_m), nodelist=nodes_m)
        
        diff = np.abs(adj_b - adj_f) + np.abs(adj_f - adj_m) + np.abs(adj_b - adj_m)
        if np.sum(diff) == 0: break
            
        worst_node = np.argmax(np.sum(diff, axis=0) + np.sum(diff, axis=1))
        current_indices.pop(worst_node)

    if current_indices:
        final_mapping = {ds: [current_mapping[ds][i] for i in current_indices] for ds in trio}
        # Final Connectivity Check
        sub = graphs['FAFB'].subgraph(final_mapping['FAFB'])
        largest_wcc = max(nx.weakly_connected_components(sub), key=len)
        
        final_n = len(largest_wcc)
        print(f"  -> SUCCESS: Found weakly connected isomorphic ML motif of size N={final_n}")
        
        final_rows = {ds: [] for ds in trio}
        for node_f in largest_wcc:
            idx = current_mapping['FAFB'].index(node_f)
            for ds in trio: final_rows[ds].append(current_mapping[ds][idx])
            
        pd.DataFrame(final_rows).to_csv("results/ml_submission.csv", index=False)

if __name__ == "__main__":
    main()
