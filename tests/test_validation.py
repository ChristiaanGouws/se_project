"""Validation Testing Suite (Black-Box Requirements & Use-Case Testing).

Formally tests UC1 through UC5, security requirements, and non-functional reliability
from the user and REST API boundary.
Test cases:
- TC1_UC1_classical_solver_validation
- TC2_UC4_token_configuration_and_security
- TC3_UC2_quantum_qaoa_execution
- TC4_UC3_timeout_and_auth_fallback_to_local_aer
- TC5_UC3_simulator_memory_limit_boundary
- TC6_UC5_comparative_analytics_and_usability
"""

import time
import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from byteflow.api.app import app
from byteflow.core.graph import GraphInstance, GraphPresets, GraphWorkspace
from byteflow.solvers.classical import ClassicalResult, ClassicalSolver
from byteflow.security.token_manager import AuthenticationError, TokenManager
from byteflow.quantum.qaoa import QAOACircuitBuilder, QiskitQAOASolver
from byteflow.quantum.fallback import (
    FallbackManager,
    SimulatorMemoryExceededError,
    TimeoutException,
)
from byteflow.analytics.comparative import (
    ComparativeAnalyticsEngine,
    ComparativeBenchmarkReport,
)


class TestByteFlowValidationSuite(unittest.TestCase):
    """Formal validation test cases exercising ByteFlow from the user/API boundary."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_records = {}

    def test_TC1_UC1_classical_solver_validation(self):
        """TC1: Functional validation of Classical Max-Cut Solver (UC1) & Alternate Flow A1."""
        t0 = time.perf_counter()

        # Action 1: Dispatch predefined 4-node diamond graph (known exact max cut = 4)
        graph = GraphPresets.diamond_4_node()
        self.assertEqual(graph.node_count, 4)
        self.assertEqual(graph.edge_count, 5)

        # 1.1 API boundary verification
        resp = self.client.post("/api/solve/classical", json={"graph_id": "4-Node Diamond"})
        self.assertEqual(resp.status_code, 200)
        api_data = resp.json()
        self.assertEqual(api_data["status"], "success")
        self.assertEqual(api_data["optimal_cut_value"], 4)
        self.assertGreater(api_data["wall_clock_runtime"], 0.0)

        # 1.2 Python Solver Module verification
        result: ClassicalResult = ClassicalSolver.solve(graph)
        self.assertEqual(result.optimal_cut_value, 4)
        self.assertEqual(result.cut_value, 4)
        self.assertEqual(result.total_edges, 5)
        self.assertEqual(result.approximation_ratio, 1.0)
        self.assertGreater(result.wall_clock_runtime, 0.0)

        # Verify partition_layout assigns every node to valid binary partition (0 or 1)
        self.assertEqual(len(result.partition_layout), graph.node_count)
        for node_id in range(graph.node_count):
            self.assertIn(node_id, result.partition_layout)
            self.assertIn(result.partition_layout[node_id], (0, 1))

        # Check partition sets partition the graph completely
        all_partition_nodes = set(result.set_s).union(set(result.set_not_s))
        self.assertEqual(all_partition_nodes, set(range(graph.node_count)))

        # Action 2: Verify Alternate Flow A1 - Malformed and empty graph inputs handled cleanly
        with self.assertRaises(ValueError):
            ClassicalSolver.solve(None)

        # Empty matrix
        with self.assertRaises(ValueError):
            ClassicalSolver.solve([])

        # API boundary error response for empty matrix
        err_resp = self.client.post("/api/solve/classical", json={"adjacency_matrix": []})
        self.assertEqual(err_resp.status_code, 400)
        self.assertIn("cannot be empty", err_resp.json()["detail"].lower())

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC1"] = {
            "name": "TC1_UC1_classical_solver_validation",
            "runtime_s": elapsed,
            "inputs": "4-Node Diamond (N=4, E=5, known max cut=4); Empty adjacency matrix []",
            "expected": "Status 200, optimal_cut_value=4, binary partition layout {0,1}, runtime > 0; 400 Bad Request on empty",
            "actual": f"optimal_cut_value={result.optimal_cut_value}, runtime={result.wall_clock_runtime*1000:.2f}ms, error handled cleanly",
        }

    def test_TC2_UC4_token_configuration_and_security(self):
        """TC2: Security & functional validation of IBM Quantum API Token handling (UC4)."""
        t0 = time.perf_counter()
        token_mgr = TokenManager()

        # Action 1: Attempt empty or whitespace token
        is_valid, err_msg = token_mgr.validate_token_format("")
        self.assertFalse(is_valid)
        self.assertIn("AuthenticationError", err_msg)
        self.assertIn("empty", err_msg.lower())

        # Attempt to configure empty token
        res_empty = token_mgr.configure_token("")
        self.assertFalse(res_empty["authenticated"])
        self.assertIsNone(token_mgr.get_session_token())  # Plaintext never stored

        # API boundary rejection of empty token
        api_resp_empty = self.client.post("/api/token/validate", json={"token": ""})
        self.assertEqual(api_resp_empty.status_code, 401)

        # Action 2: Attempt malformed token (too short or invalid chars)
        is_valid_short, err_short = token_mgr.validate_token_format("short_token_123")
        self.assertFalse(is_valid_short)
        self.assertIn("Malformed API token", err_short)

        res_malformed = token_mgr.configure_token("malformed token with spaces!#$")
        self.assertFalse(res_malformed["authenticated"])
        self.assertIsNone(token_mgr.get_session_token())  # Never stored in plaintext

        # Action 3: Configure valid token structure (e.g. 64-char hex string)
        valid_raw_token = "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90"
        res_valid = token_mgr.configure_token(valid_raw_token)
        self.assertTrue(res_valid["authenticated"])
        self.assertEqual(res_valid["status"], "success")

        # Plaintext security assertions:
        # 1. Plaintext must NOT appear in raw attributes or string representations
        self.assertNotIn(valid_raw_token, str(token_mgr))
        self.assertNotIn(valid_raw_token, repr(token_mgr))
        # 2. Token must be encrypted in memory with Fernet cipher
        self.assertNotEqual(token_mgr._encrypted_token, valid_raw_token.encode("utf-8"))
        # 3. Masked token returned for UI display
        self.assertTrue(res_valid["masked_token"].startswith("a1b2***"))
        self.assertTrue(res_valid["masked_token"].endswith("8f90"))
        # 4. Decrypted session token available strictly on demand
        self.assertEqual(token_mgr.get_session_token(), valid_raw_token)

        # API boundary acceptance of valid token
        api_resp_valid = self.client.post("/api/token/validate", json={"token": valid_raw_token})
        self.assertEqual(api_resp_valid.status_code, 200)
        self.assertTrue(api_resp_valid.json()["authenticated"])
        self.assertIn("masked_token", api_resp_valid.json())

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC2"] = {
            "name": "TC2_UC4_token_configuration_and_security",
            "runtime_s": elapsed,
            "inputs": "Empty '', malformed 'short_token_123', valid 64-char token 'a1b2...'",
            "expected": "401/AuthenticationError on empty/malformed, zero plaintext storage; encrypted Fernet session token with masked UI output",
            "actual": f"AuthenticationError rejected bad tokens; valid encrypted (masked: {res_valid['masked_token']})",
        }

    def test_TC3_UC2_quantum_qaoa_execution(self):
        """TC3: Functional validation of Qiskit QAOA execution engine (UC2) with depth p=2."""
        t0 = time.perf_counter()

        graph = GraphPresets.diamond_4_node()
        layer_depth = 2
        shots = 1024

        # 3.1 Verify conversion of adjacency matrix to Ising Spin Hamiltonian
        hamiltonian = QiskitQAOASolver.to_ising_hamiltonian(graph)
        self.assertIsNotNone(hamiltonian)
        self.assertEqual(hamiltonian.num_qubits, graph.node_count)
        # 5 edges with ZZ interactions and identity constants
        self.assertGreater(len(hamiltonian), 0)

        # 3.2 Verify parameterized QAOA circuit ansatz of depth p=2
        circuit = QiskitQAOASolver.build_ansatz(graph, layer_depth=layer_depth)
        self.assertEqual(circuit.num_qubits, graph.node_count)
        self.assertEqual(circuit.num_clbits, graph.node_count)
        ops = circuit.count_ops()
        self.assertEqual(ops.get("h", 0), 4)
        # For p=2, 5 edges * 2 CNOTs * 2 layers = 20 CNOTs
        self.assertEqual(ops.get("cx", 0), 20)
        self.assertEqual(ops.get("rz", 0), 10)
        self.assertEqual(ops.get("rx", 0), 8)
        self.assertEqual(ops.get("measure", 0), 4)

        # 3.3 Execute with mocked IBM Runtime session for deterministic offline validation
        # Qiskit Little-Endian counts: '0110' reversed is '0110' (cut 4); '1001' reversed is '1001' (cut 4)
        mock_raw_counts = {"0110": 600, "1001": 350, "0000": 74}
        mock_pub = MagicMock()
        mock_pub.data = mock_raw_counts
        mock_job = MagicMock()
        mock_job.result.return_value = [mock_pub]
        # Native Qiskit Runtime V2 job metrics with active QPU compute time (quantum_seconds)
        mock_job.metrics.return_value = {
            "usage": {"quantum_seconds": 0.045, "qpu_charge_time_seconds": 0.045}
        }
        mock_session = MagicMock()
        mock_session.backend.name = "ibm_brisbane"
        mock_session.run.return_value = mock_job

        solver = QiskitQAOASolver(backend_name="ibm_brisbane")
        result = solver.solve(
            graph=graph,
            layer_depth=layer_depth,
            shots=shots,
            session=mock_session,
            exact_max_cut=4,
        )

        # 3.4 Assertions on quantum results and true QPU compute time telemetry
        self.assertEqual(result.provenance_label, "IBM QPU")
        self.assertEqual(result.backend_name, "ibm_brisbane")
        self.assertEqual(result.cut_value, 4)
        self.assertEqual(result.total_edges, 5)
        self.assertEqual(result.shots, shots)
        self.assertFalse(result.fallback_occurred)
        self.assertIsNone(result.fallback_reason)

        # QPU compute time telemetry verification
        self.assertEqual(result.qpu_seconds, 0.045)
        self.assertEqual(result.execution_time_seconds, 0.045)
        self.assertEqual(result.wall_clock_runtime, 0.045)
        self.assertIsNotNone(result.wall_clock_overhead_seconds)
        self.assertIn("45.00 ms", result.formatted_runtime)

        # Verify fallback telemetry query mechanism (job.usage fallback)
        from byteflow.quantum.executor import extract_qpu_compute_time
        fallback_job = MagicMock()
        fallback_job.metrics.side_effect = Exception("Metrics unavailable")
        fallback_job.usage.return_value = 0.038
        self.assertEqual(extract_qpu_compute_time(fallback_job), 0.038)

        # Verify measurement counts and expectation value
        self.assertIsInstance(result.measurement_counts, dict)
        self.assertGreater(len(result.measurement_counts), 0)
        self.assertIsInstance(result.expectation_value, float)
        self.assertGreater(result.expectation_value, 0.0)

        # Verify partition layout is valid binary assignment for every node
        self.assertEqual(len(result.partition_layout), graph.node_count)
        for i in range(graph.node_count):
            self.assertIn(result.partition_layout[i], (0, 1))

        # Expected cut value calculation for verification:
        # (4 * 600 + 4 * 350 + 0 * 74) / 1024 = 3800 / 1024 = 3.7109375
        expected_expectation = 3800.0 / 1024.0
        self.assertAlmostEqual(result.expectation_value, expected_expectation, places=4)

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC3"] = {
            "name": "TC3_UC2_quantum_qaoa_execution",
            "runtime_s": elapsed,
            "inputs": f"4-Node Diamond, depth p={layer_depth}, shots={shots}, mocked IBM Session ('ibm_brisbane')",
            "expected": "Ising Hamiltonian 4-qubit, p=2 circuit (20 CX), cut_value=4, active_qpu=45.00ms, provenance='IBM QPU'",
            "actual": f"provenance='{result.provenance_label}', cut={result.cut_value}, exp_val={result.expectation_value:.4f}, active_qpu={result.qpu_seconds*1000:.2f}ms ({result.qpu_seconds:.4f}s)",
        }

    def test_TC4_UC3_timeout_and_auth_fallback_to_local_aer(self):
        """TC4: Non-functional reliability validation of Automated Fallback to local simulator (UC3)."""
        t0 = time.perf_counter()
        graph = GraphPresets.diamond_4_node()
        fb_manager = FallbackManager(timeout_limit=5.0)

        # Action 1: Simulate IBM Cloud queue timeout (job.time_in_queue > TIMEOUT_LIMIT)
        def timeout_remote_executor(**kwargs):
            raise TimeoutException(
                "IBM Quantum Cloud queue wait (6.2s) exceeded safety TIMEOUT_LIMIT (5.0s)."
            )

        res_timeout = fb_manager.execute_with_fallback(
            graph=graph,
            layer_depth=1,
            shots=256,
            remote_executor=timeout_remote_executor,
            exact_max_cut=4,
        )

        # Assertions for timeout fallback:
        self.assertTrue(res_timeout.fallback_occurred)
        self.assertEqual(res_timeout.provenance_label, "Local Sim")
        self.assertIn("TimeoutException", res_timeout.fallback_reason)
        self.assertIn("exceeded safety TIMEOUT_LIMIT", res_timeout.fallback_reason)
        self.assertGreaterEqual(res_timeout.cut_value, 2)
        self.assertGreater(len(res_timeout.measurement_counts), 0)
        self.assertGreater(res_timeout.expectation_value, 0.0)
        self.assertIsNotNone(fb_manager.last_fallback_notification)
        self.assertIn("[FALLBACK TRIGGERED]", fb_manager.last_fallback_notification)

        # Action 2: Simulate IBM Cloud AuthenticationError / credential failure
        def auth_remote_executor(**kwargs):
            raise AuthenticationError(
                "IBM Quantum Cloud 401 Unauthorized: Invalid API token credentials."
            )

        res_auth = fb_manager.execute_with_fallback(
            graph=graph,
            layer_depth=1,
            shots=256,
            remote_executor=auth_remote_executor,
            exact_max_cut=4,
        )

        # Assertions for authentication failure fallback:
        self.assertTrue(res_auth.fallback_occurred)
        self.assertEqual(res_auth.provenance_label, "Local Sim")
        self.assertIn("AuthenticationError", res_auth.fallback_reason)
        self.assertGreaterEqual(res_auth.cut_value, 2)
        self.assertGreater(len(res_auth.measurement_counts), 0)
        self.assertGreater(res_auth.expectation_value, 0.0)

        # Action 3: Verify fallback via REST API endpoint without token
        api_resp = self.client.post(
            "/api/solve/quantum",
            json={"graph_id": "4-Node Diamond", "layer_depth": 1, "shots": 128, "token": ""},
        )
        self.assertEqual(api_resp.status_code, 200)
        api_data = api_resp.json()
        self.assertTrue(api_data["fallback_occurred"])
        self.assertEqual(api_data["provenance_label"], "Local Sim")

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC4"] = {
            "name": "TC4_UC3_timeout_and_auth_fallback_to_local_aer",
            "runtime_s": elapsed,
            "inputs": "Simulated TimeoutException (6.2s > 5.0s limit) and AuthenticationError (401 Unauthorized)",
            "expected": "Caught without crash; transparent redirection to local simulator; provenance='Local Sim'; fallback notification logged",
            "actual": f"res_timeout.provenance='{res_timeout.provenance_label}', res_auth.provenance='{res_auth.provenance_label}', notification captured",
        }

    def test_TC5_UC3_simulator_memory_limit_boundary(self):
        """TC5: Reliability boundary validation when node count exceeds simulator memory threshold (UC3 A1)."""
        t0 = time.perf_counter()

        fb_manager = FallbackManager(max_simulator_qubits=25)

        # Action 1: Create a 50-node ring graph (node count = 50 > safety threshold of 25)
        large_graph = GraphPresets.ring_n_nodes(50)
        self.assertEqual(large_graph.node_count, 50)

        # Assertion: Execution must abort gracefully before allocating 2^50 state amplitudes in RAM
        with self.assertRaises(SimulatorMemoryExceededError) as ctx:
            fb_manager.execute_with_fallback(graph=large_graph)

        err_msg = str(ctx.exception)
        self.assertIn("Simulator memory limit exceeded", err_msg)
        self.assertIn("50 nodes", err_msg)
        self.assertIn("exceeds the local simulation threshold of 25 qubits", err_msg)
        self.assertIn("reduce the graph size", err_msg)

        # Action 2: REST API boundary validation with the large graph
        api_resp = self.client.post(
            "/api/solve/quantum",
            json={"graph_id": "50-Node Ring", "layer_depth": 1, "shots": 100},
        )
        self.assertEqual(api_resp.status_code, 400)
        api_detail = api_resp.json()["detail"]
        self.assertIn("Simulator memory limit exceeded", api_detail)
        self.assertIn("reduce the graph size", api_detail)

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC5"] = {
            "name": "TC5_UC3_simulator_memory_limit_boundary",
            "runtime_s": elapsed,
            "inputs": "50-Node Ring Graph (50 nodes > 25 qubit safety limit)",
            "expected": "Graceful abort with SimulatorMemoryExceededError / 400 Bad Request; prompt to reduce graph size",
            "actual": f"Caught SimulatorMemoryExceededError: '{err_msg[:65]}...'",
        }

    def test_TC6_UC5_comparative_analytics_and_usability(self):
        """TC6: Usability & functional validation of Comparative Analytics Dashboard (UC5)."""
        t0 = time.perf_counter()
        graph = GraphPresets.diamond_4_node()

        # Step 1: Query comparative view when only classical solver has been run (UC5 Alternate Flow A1)
        classical_result = ClassicalSolver.solve(graph)

        incomplete_report: ComparativeBenchmarkReport = ComparativeAnalyticsEngine.compare(
            graph=graph,
            classical_result=classical_result,
            quantum_result=None,
        )

        # Assertions for incomplete data handling:
        self.assertFalse(incomplete_report.is_complete)
        self.assertIsNotNone(incomplete_report.placeholder_guidance)
        self.assertIn("Incomplete solver data", incomplete_report.placeholder_guidance)
        self.assertIn("Quantum QAOA solver has not been executed yet", incomplete_report.placeholder_guidance)
        self.assertIn("execute the quantum solver", incomplete_report.placeholder_guidance)

        # Verify ASCII card shows clear guidance for incomplete state
        ascii_incomplete = incomplete_report.generate_ascii_summary()
        self.assertIn("INCOMPLETE STATE", ascii_incomplete)
        self.assertIn("Guidance:", ascii_incomplete)

        # Step 2: Run quantum solver and query complete comparative analytics payload
        # Use local simulator for deterministic, fast offline comparison
        from byteflow.quantum.executor import QuantumExecutor
        quantum_result = QuantumExecutor().execute_local_simulator(
            graph=graph,
            layer_depth=1,
            shots=512,
            exact_max_cut=classical_result.optimal_cut_value,
        )

        complete_report: ComparativeBenchmarkReport = ComparativeAnalyticsEngine.compare(
            graph=graph,
            classical_result=classical_result,
            quantum_result=quantum_result,
            layer_depth=1,
            exact_max_cut=classical_result.optimal_cut_value,
        )

        # Assertions for complete state:
        self.assertTrue(complete_report.is_complete)
        self.assertIsNone(complete_report.placeholder_guidance)

        # Side-by-side metrics:
        self.assertEqual(complete_report.graph_name, "4-Node Diamond")
        self.assertEqual(complete_report.node_count, 4)
        self.assertEqual(complete_report.edge_count, 5)
        self.assertEqual(complete_report.classical_cut, 4)
        self.assertGreaterEqual(complete_report.quantum_cut, 2)
        self.assertLessEqual(complete_report.quantum_cut, 5)

        # Approximation ratio bounded in [0.0, 1.0]
        self.assertIsNotNone(complete_report.approximation_ratio)
        self.assertGreaterEqual(complete_report.approximation_ratio, 0.0)
        self.assertLessEqual(complete_report.approximation_ratio, 1.0)

        # Verify partition layouts for both solvers are present and complete
        self.assertIsInstance(complete_report.classical_partition_layout, dict)
        self.assertEqual(len(complete_report.classical_partition_layout), 4)
        self.assertIsInstance(complete_report.quantum_partition_layout, dict)
        self.assertEqual(len(complete_report.quantum_partition_layout), 4)

        # Execution runtimes recorded and positive
        self.assertGreater(complete_report.classical_runtime_seconds, 0.0)
        self.assertGreater(complete_report.quantum_runtime_seconds, 0.0)

        # Solution probabilities & shot counts
        self.assertGreater(complete_report.quantum_shots, 0)
        self.assertGreaterEqual(complete_report.quantum_max_cut_probability, 0.0)

        # API boundary verification for comparative analytics
        # First ensure backend has cached classical and quantum results
        self.client.post("/api/solve/classical", json={"graph_id": "4-Node Diamond"})
        self.client.post("/api/solve/quantum", json={"graph_id": "4-Node Diamond", "layer_depth": 1, "shots": 128})
        api_comp_resp = self.client.get("/api/comparative?graph_id=4-Node+Diamond")
        self.assertEqual(api_comp_resp.status_code, 200)
        api_comp_data = api_comp_resp.json()
        self.assertTrue(api_comp_data["is_complete"])
        self.assertEqual(api_comp_data["classical_cut"], 4)
        self.assertIn("approximation_ratio", api_comp_data)

        elapsed = time.perf_counter() - t0
        self.__class__.test_records["TC6"] = {
            "name": "TC6_UC5_comparative_analytics_and_usability",
            "runtime_s": elapsed,
            "inputs": "4-Node Diamond, Phase 1: Classical only; Phase 2: Classical + Quantum QAOA",
            "expected": "Incomplete state returns placeholder guidance; complete state returns side-by-side layouts, approx_ratio in [0.0, 1.0], runtimes",
            "actual": f"Incomplete guidance returned; Complete approx_ratio={complete_report.approximation_ratio:.4f}, cut_diff={complete_report.cut_difference:+d}",
        }


if __name__ == "__main__":
    unittest.main()
