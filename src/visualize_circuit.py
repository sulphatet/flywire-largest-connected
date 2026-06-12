import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os

def visualize():
    print("Loading submission and FAFB dataset...")
    df_sub = pd.read_csv("results/submission.csv")
    df_fafb = pd.read_csv("FAFB.csv")
    df_fafb.columns = ["source", "target"]
    
    print("Building graph...")
    G = nx.from_pandas_edgelist(df_fafb, "source", "target", create_using=nx.DiGraph())
    
    nodes = df_sub["FAFB"].tolist()
    sub_G = G.subgraph(nodes)
    
    print(f"Plotting subgraph with {sub_G.number_of_nodes()} nodes and {sub_G.number_of_edges()} edges...")
    plt.figure(figsize=(14, 14))
    
    # Layout
    pos = nx.spring_layout(sub_G, seed=42, k=0.15)
    
    # Identify hubs vs leaves
    out_degrees = dict(sub_G.out_degree())
    top_hubs = [n for n, d in sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]]
    
    node_colors = ['#FF5733' if n in top_hubs else '#3498DB' for n in sub_G.nodes()]
    node_sizes = [500 if n in top_hubs else 20 for n in sub_G.nodes()]
    
    nx.draw_networkx_nodes(sub_G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.7)
    nx.draw_networkx_edges(sub_G, pos, alpha=0.15, edge_color='#7F8C8D', arrows=True, arrowsize=5)
    
    plt.title(f"Conserved Integrative Core in FAFB (N={len(nodes)})", fontsize=20, pad=20)
    
    # Create legend
    import matplotlib.lines as mlines
    hub_marker = mlines.Line2D([], [], color='#FF5733', marker='o', linestyle='None', markersize=15, label='Integrative Hubs')
    leaf_marker = mlines.Line2D([], [], color='#3498DB', marker='o', linestyle='None', markersize=5, label='Target Neurons')
    plt.legend(handles=[hub_marker, leaf_marker], loc='upper right', fontsize=12)
    
    plt.axis("off")
    os.makedirs("results", exist_ok=True)
    plt.savefig("results/circuit_graph.png", dpi=300, bbox_inches='tight', facecolor='white')
    print("Saved high-res network visualization to results/circuit_graph.png")

if __name__ == "__main__":
    visualize()
