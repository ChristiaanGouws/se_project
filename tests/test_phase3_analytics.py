"""Unit tests for Phase 3: Comparative analytics engine and benchmark reports."""

import unittest
from byteflow.core.graph import GraphPresets
from byteflow.solvers.classical import ClassicalSolver
from byteflow.quantum.executor import QuantumExecutor
from byteflow.analytics.comparative import ComparativeAnalyticsEngine


class TestComparativeAnalyticsEngine(unittest.TestCase):
    def test_comparative_report_generation(self):
        graph = GraphPresets.diamond_4_node()
        exact_res = ClassicalSolver.solve_exact_brute_force(graph)
        executor = QuantumExecutor()

        quantum_res = executor.execute_local_simulator(
            graph=graph,
            layer_depth=1,
            shots=200,
            exact_max_cut=exact_res.cut_value,
        )

        report = ComparativeAnalyticsEngine.compare(
            graph=graph,
            classical_result=exact_res,
            quantum_result=quantum_res,
            layer_depth=1,
            exact_max_cut=exact_res.cut_value,
        )

        self.assertEqual(report.graph_name, "4-Node Diamond")
        self.assertEqual(report.node_count, 4)
        self.assertEqual(report.edge_count, 5)
        self.assertEqual(report.classical_cut, 4)
        self.assertEqual(report.quantum_provenance, "Local Sim")
        self.assertGreaterEqual(report.quantum_cut, 2)
        self.assertLessEqual(report.quantum_cut, 5)

        # Ensure ASCII summary renders properly
        ascii_text = report.generate_ascii_summary()
        self.assertIn("BYTEFLOW COMPARATIVE MAX-CUT ANALYTICS BENCHMARK", ascii_text)
        self.assertIn("Approximation Ratio", ascii_text)
        self.assertIn("Local Sim", ascii_text)

        # JSON serialization check
        json_data = report.to_json()
        self.assertIn("4-node diamond", json_data.lower())


if __name__ == "__main__":
    unittest.main()
