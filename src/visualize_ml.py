import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import os

# We'll re-run the embedding logic briefly to get the plot data
import networkx as nx

def plot_alignment():
    print("Loading data for ML Manifold Visualization...")
    trio = ('BANC', 'FAFB', 'MCNS')
    all_features = []
    dataset_labels = []
    
    for ds in trio:
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        G = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())
        
        # Sample 1000 nodes for the plot to avoid clutter
        nodes = list(G.nodes())[:1000]
        in_deg = dict(G.in_degree())
        out_deg = dict(G.out_degree())
        
        for n in nodes:
            all_features.append([in_deg[n], out_deg[n], len(list(G.neighbors(n)))])
            dataset_labels.append(ds)

    features = np.array(all_features)
    # Normalize
    features = (features - np.mean(features, axis=0)) / np.std(features, axis=0)
    
    # Project 3D degrees to 2D for the "Topological Manifold"
    pca = PCA(n_components=2)
    coords = pca.fit_transform(features)
    
    plt.figure(figsize=(10, 8))
    colors = {'BANC': '#E74C3C', 'FAFB': '#2ECC71', 'MCNS': '#3498DB'}
    
    for ds in trio:
        idx = [i for i, l in enumerate(dataset_labels) if l == ds]
        plt.scatter(coords[idx, 0], coords[idx, 1], c=colors[ds], label=ds, alpha=0.5, s=20)
        
    plt.title("Structural Manifold Alignment (Unsupervised ML)", fontsize=16)
    plt.xlabel("Topological Component 1")
    plt.ylabel("Topological Component 2")
    plt.legend()
    plt.grid(True, alpha=0.2)
    
    os.makedirs("results", exist_ok=True)
    plt.savefig("results/ml_manifold.png", dpi=300, bbox_inches='tight')
    print("Saved ML Manifold visualization to results/ml_manifold.png")

if __name__ == "__main__":
    plot_alignment()
