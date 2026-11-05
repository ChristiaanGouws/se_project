"""Unit tests for Phase 2: Quantum execution and automated fallback handling."""

import unittest
from byteflow.core.graph import GraphPresets
from byteflow.quantum.executor import QuantumExecutor


class TestQuantumExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = QuantumExecutor(timeout_seconds=5.0)

    def test_local_simulator_execution(self):
        graph = GraphPresets.diamond_4_node()
        result = self.executor.execute_local_simulator(
            graph=graph,
            layer_depth=1,
            shots=256,
            exact_max_cut=4,
        )

        self.assertEqual(result.provenance_label, "Local Sim")
        self.assertEqual(result.shots, 256)
        self.assertEqual(result.total_edges, 5)
        self.assertFalse(result.fallback_occurred)
        self.assertGreaterEqual(result.cut_value, 2)
        self.assertLessEqual(result.cut_value, 4)
        self.assertGreater(result.execution_time_seconds, 0)
        self.assertEqual(len(result.best_bitstring), 4)

    def test_automated_fallback_when_token_is_missing(self):
        graph = GraphPresets.cycle_5_node()
        result = self.executor.execute_with_fallback(
            graph=graph,
            layer_depth=1,
            shots=200,
            api_token="",  # No token provided
            exact_max_cut=4,
        )

        # UC3 Fallback must activate automatically
        self.assertTrue(result.fallback_occurred)
        self.assertEqual(result.provenance_label, "Local Sim")
        self.assertIn("No IBM Quantum API token", result.fallback_reason)
        self.assertGreaterEqual(result.cut_value, 2)

    def test_automated_fallback_when_token_is_invalid(self):
        graph = GraphPresets.diamond_4_node()
        result = self.executor.execute_with_fallback(
            graph=graph,
            layer_depth=1,
            shots=150,
            api_token="INVALID_DUMMY_TOKEN_xyz123",
            exact_max_cut=4,
        )

        # Should catch authentication error and gracefully divert to local simulation
        self.assertTrue(result.fallback_occurred)
        self.assertEqual(result.provenance_label, "Local Sim")
        self.assertIsNotNone(result.fallback_reason)
        self.assertGreaterEqual(result.cut_value, 2)


if __name__ == "__main__":
    unittest.main()
