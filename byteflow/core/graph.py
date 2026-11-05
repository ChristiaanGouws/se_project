"""Core data models and graph instance abstractions for the ByteFlow platform."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union



@dataclass(frozen=True)
class GraphInstance:
    """Represents a graph instance for Max-Cut benchmarking."""
    name: str
    node_count: int
    edges: Tuple[Tuple[int, int], ...]
    description: str = ""

    def __post_init__(self) -> None:
        if self.node_count <= 0:
            raise ValueError("node_count must be positive.")
        for u, v in self.edges:
            if u == v:
                raise ValueError(f"Self-loops are not permitted in Max-Cut problem: ({u}, {v})")
            if not (0 <= u < self.node_count and 0 <= v < self.node_count):
                raise ValueError(f"Edge ({u}, {v}) references node out of bounds [0, {self.node_count - 1}].")

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def cut_value(self, bitstring: str) -> int:
        """Calculate the cut value for a binary partition bitstring.

        Nodes assigned '0' belong to set S; nodes assigned '1' belong to set V \\ S.
        """
        if len(bitstring) != self.node_count:
            raise ValueError(
                f"Bitstring length ({len(bitstring)}) must match node count ({self.node_count})."
            )
        return sum(bitstring[u] != bitstring[v] for u, v in self.edges)

    def partition_sets(self, bitstring: str) -> Tuple[List[int], List[int]]:
        """Return two lists of nodes corresponding to sets S and V \\ S."""
        set_s = [node for node, bit in enumerate(bitstring) if bit == "0"]
        set_not_s = [node for node, bit in enumerate(bitstring) if bit == "1"]
        return set_s, set_not_s

    def cut_edges(self, bitstring: str) -> List[Tuple[int, int]]:
        """Return the list of edges that cross the cut partition."""
        return [(u, v) for u, v in self.edges if bitstring[u] != bitstring[v]]

    @property
    def nodes(self) -> List[int]:
        """Return the list of vertex IDs [0, ..., node_count - 1]."""
        return list(range(self.node_count))

    @property
    def adjacency_matrix(self) -> List[List[int]]:
        """Return the symmetric adjacency matrix representing the graph."""
        matrix = [[0] * self.node_count for _ in range(self.node_count)]
        for u, v in self.edges:
            matrix[u][v] = 1
            matrix[v][u] = 1
        return matrix

    @classmethod
    def from_adjacency_matrix(
        cls,
        name: str,
        matrix: List[List[int]],
        description: str = "",
    ) -> "GraphInstance":
        """Construct a GraphInstance from an adjacency matrix."""
        n = len(matrix)
        if n <= 0:
            raise ValueError("Adjacency matrix cannot be empty.")
        for i, row in enumerate(matrix):
            if len(row) != n:
                raise ValueError(f"Row {i} length ({len(row)}) does not match square dimension ({n}).")
            if row[i] != 0:
                raise ValueError(f"Self-loops are not permitted in Max-Cut problem: node {i}.")

        edges: List[Tuple[int, int]] = []
        for u in range(n):
            for v in range(u + 1, n):
                if matrix[u][v]:
                    edges.append((u, v))

        return cls(name=name, node_count=n, edges=tuple(edges), description=description)


class GraphPresets:
    """Standard educational and benchmark graph presets."""


    @staticmethod
    def diamond_4_node() -> GraphInstance:
        """4-node diamond graph (K4 minus one edge). Max cut = 4."""
        return GraphInstance(
            name="4-Node Diamond",
            node_count=4,
            edges=((0, 1), (0, 2), (1, 2), (1, 3), (2, 3)),
            description="Classic 4-node diamond graph. 5 edges with theoretical max cut of 4.",
        )

    @staticmethod
    def cycle_5_node() -> GraphInstance:
        """5-node odd cycle (C5). Max cut = 4."""
        return GraphInstance(
            name="5-Node Cycle (C5)",
            node_count=5,
            edges=((0, 1), (1, 2), (2, 3), (3, 4), (4, 0)),
            description="5-node cycle graph. Odd cycle illustrating frustration; max cut is 4.",
        )

    @staticmethod
    def bipartite_6_node() -> GraphInstance:
        """Complete bipartite graph K_{3,3}. Max cut = 9 (all edges)."""
        edges = []
        for u in range(3):
            for v in range(3, 6):
                edges.append((u, v))
        return GraphInstance(
            name="6-Node Bipartite (K3,3)",
            node_count=6,
            edges=tuple(edges),
            description="Complete bipartite graph K3,3. Max cut equals total edge count (9).",
        )

    @staticmethod
    def petersen_10_node() -> GraphInstance:
        """Petersen graph: 10 nodes, 15 edges. Max cut = 12."""
        edges = (
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 0),  # outer 5-cycle
            (5, 7), (7, 9), (9, 6), (6, 8), (8, 5),  # inner star
            (0, 5), (1, 6), (2, 7), (3, 8), (4, 9),  # spokes
        )
        return GraphInstance(
            name="10-Node Petersen Graph",
            node_count=10,
            edges=edges,
            description="Well-known cubic symmetric graph with 10 vertices and 15 edges. Max cut is 12.",
        )

    @staticmethod
    def ring_n_nodes(n: int = 50) -> GraphInstance:
        """N-node ring graph (C_n)."""
        edges = tuple((i, (i + 1) % n) for i in range(n))
        return GraphInstance(
            name=f"{n}-Node Ring",
            node_count=n,
            edges=edges,
            description=f"Ring topology with {n} nodes and {n} edges.",
        )

    @classmethod
    def all_presets(cls) -> Dict[str, GraphInstance]:
        return {
            "4-Node Diamond": cls.diamond_4_node(),
            "5-Node Cycle (C5)": cls.cycle_5_node(),
            "6-Node Bipartite (K3,3)": cls.bipartite_6_node(),
            "10-Node Petersen": cls.petersen_10_node(),
            "50-Node Ring": cls.ring_n_nodes(50),
        }


class GraphWorkspace:
    """Manages active graph instances, predefined classroom graphs, and workbench view states."""

    def __init__(self, default_preset: str = "4-Node Diamond") -> None:
        self.presets = GraphPresets.all_presets()
        self._active_graph: GraphInstance = self.presets.get(
            default_preset, GraphPresets.diamond_4_node()
        )
        self._view_mode: str = "dual"  # "dual", "classical_only", "quantum_only"
        self._execution_history: List[Dict] = []

    @property
    def active_graph(self) -> GraphInstance:
        return self._active_graph

    @property
    def adjacency_matrix(self) -> List[List[int]]:
        return self._active_graph.adjacency_matrix

    @property
    def node_list(self) -> List[int]:
        return self._active_graph.nodes

    @property
    def view_mode(self) -> str:
        return self._view_mode

    def select_graph(self, graph_or_name) -> GraphInstance:
        """Select a graph by preset name or by GraphInstance object."""
        if isinstance(graph_or_name, str):
            if graph_or_name not in self.presets:
                raise ValueError(
                    f"Unknown graph preset '{graph_or_name}'. Available: {list(self.presets.keys())}"
                )
            self._active_graph = self.presets[graph_or_name]
        elif isinstance(graph_or_name, GraphInstance):
            self._active_graph = graph_or_name
        else:
            raise TypeError(f"Expected str or GraphInstance, received {type(graph_or_name).__name__}")
        return self._active_graph

    def reset_workspace(self) -> GraphInstance:
        """Reset workspace to initial default preset (4-Node Diamond) and dual view."""
        self._active_graph = self.presets["4-Node Diamond"]
        self._view_mode = "dual"
        self._execution_history.clear()
        return self._active_graph

    def randomise_graph(self) -> GraphInstance:
        """Select a random predefined graph preset different from current active graph."""
        import random
        candidates = [k for k in self.presets.keys() if k != self._active_graph.name]
        choice = random.choice(candidates if candidates else list(self.presets.keys()))
        self._active_graph = self.presets[choice]
        return self._active_graph

    def toggle_view(self, mode: Optional[str] = None) -> str:
        """Toggle between 'dual', 'classical_only', and 'quantum_only' workbench views."""
        valid_modes = ["dual", "classical_only", "quantum_only"]
        if mode is not None:
            if mode not in valid_modes:
                raise ValueError(f"Invalid view mode '{mode}'. Valid modes: {valid_modes}")
            self._view_mode = mode
        else:
            idx = valid_modes.index(self._view_mode)
            self._view_mode = valid_modes[(idx + 1) % len(valid_modes)]
        return self._view_mode

