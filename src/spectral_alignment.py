import pandas as pd
import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds
from scipy.linalg import orthogonal_procrustes
from scipy.spatial import KDTree
import os

def get_spectral_embedding(G, k=10):
    """
    Computes a k-dimensional spectral embedding of the graph.
    Uses the top k singular vectors of the adjacency matrix.
    """
    nodes = list(G.nodes())
    node_to_idx = {n: i for i, n in enumerate(nodes)}
    
    # Build sparse adjacency matrix
    row = []
    col = []
    for u, v in G.edges():
        row.append(node_to_idx[u])
        col.append(node_to_idx[v])
    
    A = csr_matrix((np.ones(len(row)), (row, col)), shape=(len(nodes), len(nodes)))
    
    # Compute Truncated SVD (Spectral Decomposition)
    # u and v capture the 'roles' of nodes as senders/receivers
    print(f"    Computing SVD (k={k})...", flush=True)
    u, s, vt = svds(A.astype(float), k=k)
    
    # Concatenate u and v for a full structural embedding
    embedding = np.hstack([u, vt.T])
    return nodes, embedding

def main():
    trio = ('BANC', 'FAFB', 'MCNS')
    graphs = {}
    embeddings = {}
    node_lists = {}
    
    print("Step 1: Spectral Decomposition of Connectomes...", flush=True)
    for ds in trio:
        print(f"  Embedding {ds}...", flush=True)
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        G = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        G.remove_edges_from(nx.selfloop_edges(G))
        graphs[ds] = G
        
        nodes, feats = get_spectral_embedding(G, k=8)
        node_lists[ds] = nodes
        embeddings[ds] = feats

    print("\nStep 2: Latent Manifold Synchronization (Orthogonal Procrustes)...", flush=True)
    # We will align BANC and MCNS to the FAFB reference manifold.
    # Since we don't have true identity, we use 'topological landmarks' (high-degree nodes)
    # to find the rotation matrix.
    
    def get_landmarks(ds, n=100):
        # Pick top N hubs as landmarks for rotation
        out_deg = dict(graphs[ds].out_degree())
        sorted_nodes = sorted(out_deg.items(), key=lambda x: x[1], reverse=True)[:n]
        indices = [node_lists[ds].index(node) for node, _ in sorted_nodes]
        return embeddings[ds][indices]

    landmarks_fafb = get_landmarks('FAFB')
    
    aligned_embeddings = {'FAFB': embeddings['FAFB']}
    
    for ds in ['BANC', 'MCNS']:
        print(f"  Aligning {ds} manifold to FAFB reference...", flush=True)
        landmarks_ds = get_landmarks(ds)
        
        # Find optimal rotation matrix R to minimize ||L_fafb - L_ds @ R||
        R, _ = orthogonal_procrustes(landmarks_ds, landmarks_fafb)
        
        # Rotate the entire dataset manifold
        aligned_embeddings[ds] = embeddings[ds] @ R

    print("\nStep 3: Spectral KD-Tree Matching...", flush=True)
    tree_banc = KDTree(aligned_embeddings['BANC'])
    tree_mcns = KDTree(aligned_embeddings['MCNS'])
    
    # Query FAFB against aligned manifolds
    dist_banc, idx_banc = tree_banc.query(aligned_embeddings['FAFB'], k=1)
    dist_mcns, idx_mcns = tree_mcns.query(aligned_embeddings['FAFB'], k=1)
    
    total_dist = dist_banc + dist_mcns
    best_matches = np.argsort(total_dist)
    
    # Form candidate motif
    K_target = 300
    candidate_mapping = {ds: [] for ds in trio}
    used = {ds: set() for ds in trio}
    
    for f_idx in best_matches:
        b_idx = idx_banc[f_idx]
        m_idx = idx_mcns[f_idx]
        
        # Trio order is ('BANC', 'FAFB', 'MCNS')
        nodes = [node_lists['BANC'][b_idx], node_lists['FAFB'][f_idx], node_lists['MCNS'][m_idx]]
        if not any(nodes[i] in used[trio[i]] for i in range(3)):
            for i in range(3):
                candidate_mapping[trio[i]].append(nodes[i])
                used[trio[i]].add(nodes[i])
        if len(candidate_mapping['FAFB']) >= K_target: break

    print(f"\nStep 4: Adversarial Pruning of Spectral Motif (N={len(candidate_mapping['FAFB'])})...", flush=True)
    current_indices = list(range(len(candidate_mapping['FAFB'])))
    while current_indices:
        nodes_b = [candidate_mapping['BANC'][i] for i in current_indices]
        nodes_f = [candidate_mapping['FAFB'][i] for i in current_indices]
        nodes_m = [candidate_mapping['MCNS'][i] for i in current_indices]
        
        adj_b = nx.to_numpy_array(graphs['BANC'].subgraph(nodes_b), nodelist=nodes_b)
        adj_f = nx.to_numpy_array(graphs['FAFB'].subgraph(nodes_f), nodelist=nodes_f)
        adj_m = nx.to_numpy_array(graphs['MCNS'].subgraph(nodes_m), nodelist=nodes_m)
        
        diff = np.abs(adj_b - adj_f) + np.abs(adj_f - adj_m) + np.abs(adj_b - adj_m)
        if np.sum(diff) == 0: break
        
        # Prune worst offender
        worst = np.argmax(np.sum(diff, axis=0) + np.sum(diff, axis=1))
        current_indices.pop(worst)

    if current_indices:
        n_final = len(current_indices)
        # Check connectivity
        sub = graphs['FAFB'].subgraph([candidate_mapping['FAFB'][i] for i in current_indices])
        wccs = sorted(nx.weakly_connected_components(sub), key=len, reverse=True)
        n_connected = len(wccs[0]) if wccs else 0
        
        print(f"  -> SUCCESS: Found isomorphic spectral motif of size N={n_final} (Largest WCC: {n_connected})")
        
        final_rows = {ds: [] for ds in trio}
        # Keep only the largest WCC for the submission
        target_nodes = wccs[0]
        for i in current_indices:
            if candidate_mapping['FAFB'][i] in target_nodes:
                for ds in trio: final_rows[ds].append(candidate_mapping[ds][i])
                
        pd.DataFrame(final_rows).to_csv("results/spectral_submission.csv", index=False)
        print("Result saved to results/spectral_submission.csv")

if __name__ == "__main__":
    main()
