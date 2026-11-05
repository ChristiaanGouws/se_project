"""Classical baseline solvers for the Max-Cut problem."""

import itertools
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from byteflow.core.graph import GraphInstance


@dataclass(frozen=True)
class ClassicalResult:
    """Standardized result returned by classical solvers."""
    algorithm_name: str
    best_bitstring: str
    cut_value: int
    total_edges: int
    approximation_ratio: float
    evaluated_states: int
    execution_time_seconds: float
    set_s: List[int]
    set_not_s: List[int]

    @property
    def cut_percentage(self) -> float:
        return (self.cut_value / self.total_edges * 100.0) if self.total_edges > 0 else 0.0

    @property
    def optimal_cut_value(self) -> int:
        """Alias for cut_value representing optimal cut found."""
        return self.cut_value

    @property
    def wall_clock_runtime(self) -> float:
        """Execution duration in seconds."""
        return self.execution_time_seconds

    @property
    def partition_layout(self) -> dict:
        """Map each vertex index to its binary partition (0 or 1)."""
        return {i: int(bit) for i, bit in enumerate(self.best_bitstring)}

    def to_dict(self) -> dict:
        return {
            "algorithm_name": self.algorithm_name,
            "best_bitstring": self.best_bitstring,
            "cut_value": self.cut_value,
            "optimal_cut_value": self.optimal_cut_value,
            "total_edges": self.total_edges,
            "approximation_ratio": self.approximation_ratio,
            "evaluated_states": self.evaluated_states,
            "execution_time_seconds": self.execution_time_seconds,
            "wall_clock_runtime": self.wall_clock_runtime,
            "partition_layout": self.partition_layout,
            "set_s": self.set_s,
            "set_not_s": self.set_not_s,
            "cut_percentage": self.cut_percentage,
        }


class ClassicalSolver:
    """Executes deterministic and heuristic classical algorithms for Max-Cut (UC1)."""

    @classmethod
    def solve(cls, graph, method: str = "auto") -> ClassicalResult:
        """Execute classical solver with input validation per UC1 & Alternate Flow A1."""
        if graph is None:
            raise ValueError("Graph input cannot be None.")

        # Convert adjacency matrix or dict to GraphInstance if needed
        if isinstance(graph, list):
            if len(graph) == 0:
                raise ValueError("Adjacency matrix cannot be empty.")
            graph = GraphInstance.from_adjacency_matrix("Custom Graph", graph)
        elif isinstance(graph, dict):
            if "adjacency_matrix" in graph:
                graph = GraphInstance.from_adjacency_matrix(
                    graph.get("name", "Custom Graph"), graph["adjacency_matrix"]
                )
            elif "node_count" in graph and "edges" in graph:
                graph = GraphInstance(
                    name=graph.get("name", "Custom Graph"),
                    node_count=graph["node_count"],
                    edges=tuple(tuple(e) for e in graph["edges"]),
                    description=graph.get("description", ""),
                )
            else:
                raise ValueError("Dictionary must contain 'adjacency_matrix' or ('node_count' and 'edges').")
        elif not isinstance(graph, GraphInstance):
            raise TypeError(f"Expected GraphInstance, adjacency matrix, or dict, got {type(graph).__name__}")

        # Check for empty graph or graph with no edges
        if graph.node_count <= 0:
            raise ValueError("Graph must contain at least 1 node.")
        if graph.edge_count <= 0:
            raise ValueError("Graph must contain at least 1 edge for Max-Cut optimization.")

        if method == "exact" or (method == "auto" and graph.node_count <= 16):
            return cls.solve_exact_brute_force(graph)
        return cls.solve_greedy_local_search(graph)

    @staticmethod
    def solve_exact_brute_force(graph: GraphInstance) -> ClassicalResult:

        """Find the optimal Max-Cut by evaluating all 2^N partitions.

        Note: Suitable for small graphs (N <= 16) to establish ground truth
        approximation ratios for quantum evaluations.
        """
        if graph.node_count > 20:
            raise ValueError(
                f"Brute force is infeasible for N={graph.node_count} nodes (2^{graph.node_count} states)."
            )

        start_time = time.perf_counter()
        best_cut = -1
        best_bitstring = "0" * graph.node_count
        evaluated = 0

        # Optimization: fixing node 0 to '0' breaks global bit-flip symmetry (cuts search space by half)
        for combo in itertools.product("01", repeat=graph.node_count - 1):
            bitstring = "0" + "".join(combo)
            evaluated += 1
            c = graph.cut_value(bitstring)
            if c > best_cut:
                best_cut = c
                best_bitstring = bitstring
                if best_cut == graph.edge_count:
                    # Can't beat all edges cut
                    break

        elapsed = time.perf_counter() - start_time
        set_s, set_not_s = graph.partition_sets(best_bitstring)

        return ClassicalResult(
            algorithm_name="Exact Brute-Force",
            best_bitstring=best_bitstring,
            cut_value=best_cut,
            total_edges=graph.edge_count,
            approximation_ratio=1.0,  # Exact optimum
            evaluated_states=evaluated,
            execution_time_seconds=elapsed,
            set_s=set_s,
            set_not_s=set_not_s,
        )

    @staticmethod
    def solve_greedy_local_search(
        graph: GraphInstance,
        exact_max_cut: Optional[int] = None,
        max_restarts: int = 5,
    ) -> ClassicalResult:
        """Find a fast classical baseline using multi-start greedy local search.

        Flips individual vertex assignments greedily whenever it increases the cut value.
        Guaranteed >= 0.5 approximation ratio on any undirected graph.
        """
        start_time = time.perf_counter()
        n = graph.node_count
        best_overall_cut = -1
        best_overall_bitstring = "0" * n
        total_evaluations = 0

        # Multi-start to avoid suboptimal local optima
        for restart in range(max_restarts):
            # First restart starts at all zeros, subsequent restarts use alternate seeds
            if restart == 0:
                partition = ["0"] * n
            else:
                partition = ["1" if (i + restart) % 2 == 0 else "0" for i in range(n)]

            improved = True
            while improved:
                improved = False
                current_cut = graph.cut_value("".join(partition))
                for node in range(n):
                    partition[node] = "1" if partition[node] == "0" else "0"
                    total_evaluations += 1
                    candidate_cut = graph.cut_value("".join(partition))
                    if candidate_cut > current_cut:
                        current_cut = candidate_cut
                        improved = True
                    else:
                        partition[node] = "1" if partition[node] == "0" else "0"

            bitstring = "".join(partition)
            final_cut = graph.cut_value(bitstring)
            if final_cut > best_overall_cut:
                best_overall_cut = final_cut
                best_overall_bitstring = bitstring

        elapsed = time.perf_counter() - start_time
        set_s, set_not_s = graph.partition_sets(best_overall_bitstring)

        # Calculate approximation ratio if exact ground truth is provided
        approx_ratio = (best_overall_cut / exact_max_cut) if exact_max_cut else (best_overall_cut / graph.edge_count)

        return ClassicalResult(
            algorithm_name="Greedy Local Search",
            best_bitstring=best_overall_bitstring,
            cut_value=best_overall_cut,
            total_edges=graph.edge_count,
            approximation_ratio=min(1.0, approx_ratio),
            evaluated_states=total_evaluations,
            execution_time_seconds=elapsed,
            set_s=set_s,
            set_not_s=set_not_s,
        )
