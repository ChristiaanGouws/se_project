"""Unit tests for Phase 1: Core graph models, classical solvers, and QAOA circuits."""

import unittest
from byteflow.core.graph import GraphInstance, GraphPresets
from byteflow.solvers.classical import ClassicalSolver
from byteflow.quantum.qaoa import QAOACircuitBuilder


class TestGraphInstance(unittest.TestCase):
    def test_diamond_graph_cut_values(self):
        graph = GraphPresets.diamond_4_node()
        self.assertEqual(graph.node_count, 4)
        self.assertEqual(graph.edge_count, 5)

        # All zeros -> 0 cut
        self.assertEqual(graph.cut_value("0000"), 0)
        # Optimal partition for diamond: nodes (0, 3) vs (1, 2)
        # 0: S, 1: !S, 2: !S, 3: S -> bitstring '0110'
        # Edges cut: (0,1), (0,2), (1,3), (2,3) = 4 edges!
        self.assertEqual(graph.cut_value("0110"), 4)

    def test_invalid_bitstring_length(self):
        graph = GraphPresets.cycle_5_node()
        with self.assertRaises(ValueError):
            graph.cut_value("0101")  # Length 4 instead of 5


class TestClassicalSolvers(unittest.TestCase):
    def test_exact_brute_force_diamond(self):
        graph = GraphPresets.diamond_4_node()
        result = ClassicalSolver.solve_exact_brute_force(graph)
        self.assertEqual(result.cut_value, 4)
        self.assertEqual(result.total_edges, 5)
        self.assertEqual(result.approximation_ratio, 1.0)
        self.assertIn(result.best_bitstring, ["0110", "1001"])

    def test_exact_brute_force_c5(self):
        graph = GraphPresets.cycle_5_node()
        result = ClassicalSolver.solve_exact_brute_force(graph)
        # In C5, max cut is 4
        self.assertEqual(result.cut_value, 4)

    def test_greedy_local_search_diamond(self):
        graph = GraphPresets.diamond_4_node()
        result = ClassicalSolver.solve_greedy_local_search(graph, exact_max_cut=4)
        # Greedy local search should achieve at least 3 or 4
        self.assertGreaterEqual(result.cut_value, 3)
        self.assertGreaterEqual(result.approximation_ratio, 0.75)


class TestQAOACircuitBuilder(unittest.TestCase):
    def test_build_p1_circuit(self):
        graph = GraphPresets.diamond_4_node()
        circuit = QAOACircuitBuilder.build_circuit(graph, layer_depth=1)
        self.assertEqual(circuit.num_qubits, 4)
        self.assertEqual(circuit.num_clbits, 4)

        # Count operations:
        # 4 H gates, 5 * 2 CNOTs = 10 CNOTs, 5 Rz gates, 4 Rx gates, 4 measurements
        ops = circuit.count_ops()
        self.assertEqual(ops.get("h", 0), 4)
        self.assertEqual(ops.get("cx", 0), 10)
        self.assertEqual(ops.get("rz", 0), 5)
        self.assertEqual(ops.get("rx", 0), 4)
        self.assertEqual(ops.get("measure", 0), 4)

    def test_build_p2_circuit(self):
        graph = GraphPresets.cycle_5_node()
        circuit = QAOACircuitBuilder.build_circuit(graph, layer_depth=2)
        self.assertEqual(circuit.num_qubits, 5)
        ops = circuit.count_ops()
        # For p=2 on 5 edges: 5*2=10 Rz gates, 10*2=20 CNOTs, 5*2=10 Rx gates
        self.assertEqual(ops.get("rz", 0), 10)
        self.assertEqual(ops.get("cx", 0), 20)
        self.assertEqual(ops.get("rx", 0), 10)


if __name__ == "__main__":
    unittest.main()
