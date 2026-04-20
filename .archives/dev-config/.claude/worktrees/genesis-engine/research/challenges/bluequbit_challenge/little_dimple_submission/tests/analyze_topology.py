import networkx as nx


def analyze_connectivity(qasm_path):
    edges = []
    qubits = set()
    with open(qasm_path) as f:
        for line in f:
            if line.startswith("cz") or line.startswith("cx") or line.startswith("swap"):
                # Extract qubits
                parts = line.strip().replace(";", "").replace(",", " ").split()
                qs = [int(p.split("[")[1].split("]")[0]) for p in parts if "[" in p]
                if len(qs) == 2:
                    edges.append(tuple(sorted(qs)))
                    qubits.add(qs[0])
                    qubits.add(qs[1])

    G = nx.Graph()
    G.add_edges_from(edges)

    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    print(f"Density: {nx.density(G):.4f}")
    print(f"Diameter: {nx.diameter(G) if nx.is_connected(G) else 'Disconnected'}")

    # Check degree distribution
    degrees = [d for n, d in G.degree()]
    print(f"Max Degree: {max(degrees)}")
    print(f"Avg Degree: {sum(degrees) / len(degrees):.2f}")

    # Heuristic for geometry
    if max(degrees) <= 2:
        print("Topology: 1D Line (MPS ideal)")
    elif max(degrees) <= 4:
        print("Topology: Likely 2D Grid (PEPS ideal)")
    else:
        print("Topology: High Connectivity / Complex (General TN / Slicing)")


if __name__ == "__main__":
    analyze_connectivity("P1_little_dimple.qasm")
