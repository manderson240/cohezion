import logging
from typing import Dict, List, Set, Any
import networkx as nx

logger = logging.getLogger(__name__)

class PlasmaFilaments:
    """
    Cosmic Connectivity Layer (Gateway 27).

    Models information flow as plasma filaments (graph edges)
    conducting currents (data) between nodes (agents/concepts).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlasmaFilaments, cls).__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.graph = nx.Graph()
        self.max_current = 100.0

    def establish_filament(self, node_a: str, node_b: str, conductance: float = 1.0):
        """
        Create or strengthen a connection between two nodes.
        Conductance represents the bandwidth/affinity between nodes.
        """
        if self.graph.has_edge(node_a, node_b):
            # strengthen existing filament
            self.graph[node_a][node_b]['conductance'] += conductance
        else:
            self.graph.add_edge(node_a, node_b, conductance=conductance)

        logger.info(f"🌌 Filament Established: {node_a} <--> {node_b} (σ={conductance})")

    def conduct_impulse(self, start_node: str, payload: Any, max_depth: int = 2) -> List[str]:
        """
        Send a thought impulse across the network.
        Returns list of nodes reached.
        """
        if start_node not in self.graph:
            return []

        reached = set()
        queue = [(start_node, 0)]

        while queue:
            current_node, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            reached.add(current_node)

            # Find neighbors with sufficient conductance
            for neighbor in self.graph.neighbors(current_node):
                conductance = self.graph[current_node][neighbor]['conductance']
                if conductance > 0.5: # Threshold
                    if neighbor not in reached:
                        queue.append((neighbor, depth + 1))

        return list(reached)

def get_plasma_filaments() -> PlasmaFilaments:
    return PlasmaFilaments()
