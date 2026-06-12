import pandas as pd
import networkx as nx
import time
from collections import defaultdict
import os
import sys

# Increase recursion depth for deep connectomic matching
sys.setrecursionlimit(20000)

class ConnectedMcSplitSolver:
    def __init__(self, graphs, trio, time_limit=600):
        self.graphs = graphs
        self.trio = trio
        self.max_size = 0
        self.best_mapping = []
        self.time_limit = time_limit
        self.start_time = time.time()
        
        # Access internal NetworkX structures for O(1) adjacency checks
        print("  Initializing adjacency pointers...", flush=True)
        self.adj_in = {ds: graphs[ds].pred for ds in trio}
        self.adj_out = {ds: graphs[ds].succ for ds in trio}

    def get_bound(self, classes):
        return sum(min(len(c[0]), len(c[1]), len(c[2])) for c in classes)

    def solve(self, mapping, classes, connected_classes_idx):
        """
        mapping: list of (v, w, x)
        classes: list of (C1, C2, C3)
        connected_classes_idx: set of indices in `classes` that contain nodes connected to mapping
        """
        if time.time() - self.start_time > self.time_limit:
            return

        depth = len(mapping)
        if depth > self.max_size:
            self.max_size = depth
            self.best_mapping = list(mapping)
            if depth % 100 == 0:
                print(f"  [Connected McSplit] Depth {depth} reached...", flush=True)

        if not connected_classes_idx:
            return

        # Pruning
        if depth + self.get_bound([classes[i] for i in connected_classes_idx]) <= self.max_size:
            return

        # Heuristic: Pick a connected class with the smallest min-size
        idx = min(connected_classes_idx, key=lambda i: min(len(classes[i][0]), len(classes[i][1]), len(classes[i][2])))
        c1, c2, c3 = classes[idx]
        
        # Branch 1: Match v
        v = c1.pop()
        branch_limit = 2
        tried = 0
        for w in c2:
            for x in c3:
                tried += 1
                if tried > branch_limit: break
                
                # Refine ALL classes and update connected indices
                new_classes, new_connected_idx = self.refine(classes, connected_classes_idx, v, w, x)
                self.solve(mapping + [(v, w, x)], new_classes, new_connected_idx)
            if tried > branch_limit: break
                
        # Branch 2: Do not match v
        # We must keep the class in connected_classes_idx if it's not empty
        if not c1:
            connected_classes_idx.remove(idx)
        self.solve(mapping, classes, connected_classes_idx)

    def refine(self, classes, connected_idx, v, w, x):
        new_classes = []
        new_connected_idx = set()
        
        v_in, v_out = self.adj_in[self.trio[0]][v], self.adj_out[self.trio[0]][v]
        w_in, w_out = self.adj_in[self.trio[1]][w], self.adj_out[self.trio[1]][w]
        x_in, x_out = self.adj_in[self.trio[2]][x], self.adj_out[self.trio[2]][x]

        for i, (d1, d2, d3) in enumerate(classes):
            p1 = [[] for _ in range(4)]
            for n in d1: p1[(1 if n in v_in else 0) | (2 if n in v_out else 0)].append(n)
            p2 = [[] for _ in range(4)]
            for n in d2: p2[(1 if n in w_in else 0) | (2 if n in w_out else 0)].append(n)
            p3 = [[] for _ in range(4)]
            for n in d3: p3[(1 if n in x_in else 0) | (2 if n in x_out else 0)].append(n)
            
            for j in range(4):
                if p1[j] and p2[j] and p3[j]:
                    new_idx = len(new_classes)
                    new_classes.append((p1[j], p2[j], p3[j]))
                    # If this class was already connected, it stays connected
                    # OR if it's connected to the NEW match (j > 0), it becomes connected
                    if i in connected_idx or j > 0:
                        new_connected_idx.add(new_idx)
                        
        return new_classes, new_connected_idx

def main():
    trio = ('BANC', 'FAFB', 'MCNS')
    graphs = {}
    print("Loading graphs...", flush=True)
    for ds in trio:
        df = pd.read_csv(f"{ds}.csv")
        df.columns = ["source", "target"]
        graphs[ds] = nx.from_pandas_edgelist(df, source="source", target="target", create_using=nx.DiGraph())

    # Initial classes based on degrees
    def get_labels(G):
        return {n: (G.in_degree(n), G.out_degree(n)) for n in G.nodes()}
    labels = {ds: get_labels(graphs[ds]) for ds in trio}
    class_map = defaultdict(lambda: [[] for _ in range(3)])
    for i, ds in enumerate(trio):
        for node, lbl in labels[ds].items():
            class_map[lbl][i].append(node)
    initial_classes = [tuple(lists) for lbl, lists in class_map.items() if all(lists)]
    
    # Sort to pick a high-degree Hub as the FIRST match to start connectivity
    initial_classes.sort(key=lambda c: (sum(labels[trio[0]][c[0][0]]), -min(len(x) for x in c)), reverse=True)
    
    solver = ConnectedMcSplitSolver(graphs, trio, time_limit=600)
    
    # Start search from each of the top 10 hubs to find the best connected component
    best_overall_mapping = []
    max_overall_size = 0
    
    for seed_idx in range(min(10, len(initial_classes))):
        c1, c2, c3 = initial_classes[seed_idx]
        v = c1[0] # Take first hub
        for w in c2[:2]: # Try matching with top 2 candidates
            for x in c3[:2]:
                print(f"\nStarting search from hub triplet: ({v}, {w}, {x})...", flush=True)
                # Initial connected index is the neighbors of this seed triplet
                new_classes, new_connected_idx = solver.refine(initial_classes, set(), v, w, x)
                solver.solve([(v, w, x)], new_classes, new_connected_idx)
                
                if solver.max_size > max_overall_size:
                    max_overall_size = solver.max_size
                    best_overall_mapping = solver.best_mapping

    if best_overall_mapping:
        print(f"\nConnected McSplit found isomorphic subgraph of size: {max_overall_size}")
        rows = []
        for t in best_overall_mapping:
            rows.append({trio[0]: t[0], trio[1]: t[1], trio[2]: t[2]})
        os.makedirs("results", exist_ok=True)
        pd.DataFrame(rows).to_csv("results/submission.csv", index=False)
        print("Results saved in results/submission.csv")
    else:
        print("No result found.")

if __name__ == "__main__":
    main()
