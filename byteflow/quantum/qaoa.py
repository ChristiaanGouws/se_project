"""Quantum Approximate Optimization Algorithm (QAOA) circuit generator."""

from math import pi
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from qiskit import QuantumCircuit
from byteflow.core.graph import GraphInstance


class QAOACircuitBuilder:
    """Builds parameterized QAOA quantum circuits for Max-Cut problems."""

    @staticmethod
    def build_circuit(
        graph: GraphInstance,
        layer_depth: int = 1,
        gamma: Optional[Union[float, List[float]]] = None,
        beta: Optional[Union[float, List[float]]] = None,
    ) -> QuantumCircuit:
        """Construct a p-layer QAOA circuit for the given graph.

        Args:
            graph: GraphInstance containing nodes and edges.
            layer_depth: Integer p (number of QAOA alternating operator layers).
            gamma: Problem Hamiltonian angle(s). Defaults to pi / 4 per layer.
            beta: Mixer Hamiltonian angle(s). Defaults to pi / 8 per layer.

        Returns:
            Qiskit QuantumCircuit with measurement on all qubits.
        """
        if layer_depth < 1:
            raise ValueError("layer_depth must be at least 1.")

        # Normalize gamma and beta to lists of length layer_depth
        if gamma is None:
            gammas = [pi / 4] * layer_depth
        elif isinstance(gamma, (int, float)):
            gammas = [float(gamma)] * layer_depth
        else:
            if len(gamma) != layer_depth:
                raise ValueError(f"gamma list length ({len(gamma)}) must match layer_depth ({layer_depth}).")
            gammas = list(gamma)

        if beta is None:
            betas = [pi / 8] * layer_depth
        elif isinstance(beta, (int, float)):
            betas = [float(beta)] * layer_depth
        else:
            if len(beta) != layer_depth:
                raise ValueError(f"beta list length ({len(beta)}) must match layer_depth ({layer_depth}).")
            betas = list(beta)

        num_qubits = graph.node_count
        circuit = QuantumCircuit(num_qubits, num_qubits, name=f"QAOA_MaxCut_p{layer_depth}")

        # Step 1: Initialize uniform superposition with Hadamard gates
        circuit.h(range(num_qubits))
        circuit.barrier()

        # Step 2: Alternate between Problem Unitary U(C, gamma) and Mixer Unitary U(B, beta)
        for p in range(layer_depth):
            p_gamma = gammas[p]
            p_beta = betas[p]

            # Problem Hamiltonian: ZZ interaction on each edge (u, v)
            # exp(-i * gamma * Z_u * Z_v) implemented via CNOT - Rz(2 * gamma) - CNOT
            for u, v in graph.edges:
                circuit.cx(u, v)
                circuit.rz(2.0 * p_gamma, v)
                circuit.cx(u, v)

            circuit.barrier()

            # Mixer Hamiltonian: X rotations on each qubit
            # exp(-i * beta * X_u) implemented via Rx(2 * beta)
            for qubit in range(num_qubits):
                circuit.rx(2.0 * p_beta, qubit)

            circuit.barrier()

        # Step 3: Measurement of all qubits in computational basis
        circuit.measure(range(num_qubits), range(num_qubits))
        return circuit

    @staticmethod
    def to_ising_hamiltonian(graph: GraphInstance):
        """Convert graph adjacency to an Ising Spin Hamiltonian for Max-Cut:
        H_C = sum_{(u,v) in E} 0.5 * (I - Z_u Z_v)
        """
        from qiskit.quantum_info import SparsePauliOp

        num_qubits = graph.node_count
        if not graph.edges:
            return SparsePauliOp.from_list([("I" * num_qubits, 0.0)])

        pauli_list = []
        for u, v in graph.edges:
            # Qiskit Pauli string ordering: qubit 0 is at rightmost position
            chars = ["I"] * num_qubits
            chars[num_qubits - 1 - u] = "Z"
            chars[num_qubits - 1 - v] = "Z"
            pauli_list.append(("".join(chars), -0.5))
            pauli_list.append(("I" * num_qubits, 0.5))

        return SparsePauliOp.from_list(pauli_list).simplify()


class QiskitQAOASolver:
    """Quantum execution engine for solving Max-Cut using QAOA on IBM Quantum hardware (UC2)."""

    def __init__(self, backend_name: str = "ibm_brisbane") -> None:
        self.backend_name = backend_name

    @staticmethod
    def to_ising_hamiltonian(graph: GraphInstance):
        """Convert graph to Ising Spin Hamiltonian."""
        return QAOACircuitBuilder.to_ising_hamiltonian(graph)

    @staticmethod
    def build_ansatz(
        graph: GraphInstance,
        layer_depth: int = 1,
        gamma: Optional[Union[float, List[float]]] = None,
        beta: Optional[Union[float, List[float]]] = None,
    ) -> QuantumCircuit:
        """Build parameterized QAOA circuit ansatz."""
        return QAOACircuitBuilder.build_circuit(graph, layer_depth=layer_depth, gamma=gamma, beta=beta)

    @staticmethod
    def compute_expectation_value(
        graph: GraphInstance, measurement_counts: dict
    ) -> float:
        """Compute quantum expectation value <C> from measurement shot distribution."""
        total_shots = sum(measurement_counts.values())
        if total_shots <= 0:
            return 0.0
        weighted_cut_sum = sum(
            graph.cut_value(bitstring) * count for bitstring, count in measurement_counts.items()
        )
        return float(weighted_cut_sum / total_shots)

    def solve(
        self,
        graph: GraphInstance,
        layer_depth: int = 1,
        shots: int = 1024,
        token: Optional[str] = None,
        session=None,
        exact_max_cut: Optional[int] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        """Submit and execute QAOA circuit on IBM Quantum hardware or provided session."""
        import time
        from byteflow.quantum.executor import (
            QuantumExecutionResult,
            extract_counts_from_pub_result,
            extract_qpu_compute_time,
        )

        log = log_callback or (lambda msg: None)
        start_time = time.perf_counter()

        # Step 1: Convert graph adjacency to Ising Spin Hamiltonian
        hamiltonian = self.to_ising_hamiltonian(graph)
        log(f"Generated Ising Hamiltonian with {len(hamiltonian)} Pauli operators.")

        # Step 2: Build QAOA circuit ansatz
        circuit = self.build_ansatz(graph, layer_depth=layer_depth)
        log(f"Constructed {layer_depth}-layer QAOA circuit with {circuit.num_qubits} qubits.")

        raw_counts = {}
        backend_used = self.backend_name
        qpu_time: Optional[float] = None

        if session is not None:
            # Execute with provided session / sampler (e.g., in mocked tests or custom session)
            log("Executing QAOA on provided IBM Quantum session...")
            job = session.run([circuit], shots=shots)
            res = job.result()
            # Extract true active QPU hardware compute time from job telemetry
            qpu_time = extract_qpu_compute_time(job)

            if hasattr(res, "__getitem__"):
                raw_counts = extract_counts_from_pub_result(res[0])
            elif hasattr(res, "get_counts"):
                raw_counts = res.get_counts()
            elif isinstance(res, dict):
                raw_counts = res
            else:
                raw_counts = extract_counts_from_pub_result(res)
            if hasattr(session, "backend"):
                backend_obj = getattr(session, "backend")
                backend_used = getattr(backend_obj, "name", str(backend_obj))
        else:
            # Live IBM Quantum execution via Qiskit Runtime
            from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as RemoteSampler
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

            service = QiskitRuntimeService(token=token.strip() if token else None)
            backend = service.least_busy(simulator=False, operational=True, min_num_qubits=graph.node_count)
            backend_used = backend.name
            log(f"Connected to IBM Quantum Cloud processor: {backend_used}")

            pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
            isa_circuit = pm.run(circuit)

            sampler = RemoteSampler(mode=backend)
            job = sampler.run([isa_circuit], shots=shots)
            result = job.result()
            qpu_time = extract_qpu_compute_time(job)
            raw_counts = extract_counts_from_pub_result(result[0])

        total_wall_clock = time.perf_counter() - start_time
        if qpu_time is not None:
            effective_runtime = qpu_time
            log(
                f"Extracted true active QPU hardware compute time: {qpu_time * 1000.0:.2f} ms "
                f"({qpu_time:.4f} s) [Hardware queue + network latency: {total_wall_clock:.2f} s]"
            )
        else:
            effective_runtime = total_wall_clock
            log(f"Execution completed in {total_wall_clock:.3f} s.")

        # Account for Qiskit's little-endian bitstring ordering
        # Reverse bitstrings so bit i corresponds to vertex i
        transformed_counts = {}
        cut_histogram = {}
        for raw_bits, freq in raw_counts.items():
            norm_bits = raw_bits[::-1]
            transformed_counts[norm_bits] = freq
            cut = graph.cut_value(norm_bits)
            cut_histogram[cut] = cut_histogram.get(cut, 0) + freq

        best_cut = max(cut_histogram.keys()) if cut_histogram else 0
        shots_with_best_cut = cut_histogram.get(best_cut, 0)
        best_prob = (shots_with_best_cut / shots * 100.0) if shots > 0 else 0.0

        candidates = {b: freq for b, freq in transformed_counts.items() if graph.cut_value(b) == best_cut}
        winning_bitstring = max(candidates.items(), key=lambda it: it[1])[0] if candidates else "0" * graph.node_count
        set_s, set_not_s = graph.partition_sets(winning_bitstring)
        expectation_val = self.compute_expectation_value(graph, transformed_counts)

        approx_ratio = (best_cut / exact_max_cut) if exact_max_cut else (best_cut / graph.edge_count)

        return QuantumExecutionResult(
            provenance_label="IBM QPU",
            backend_name=backend_used,
            shots=shots,
            best_bitstring=winning_bitstring,
            cut_value=best_cut,
            total_edges=graph.edge_count,
            approximation_ratio=min(1.0, approx_ratio),
            best_cut_probability=best_prob,
            execution_time_seconds=effective_runtime,
            measurement_counts=transformed_counts,
            cut_histogram=cut_histogram,
            set_s=set_s,
            set_not_s=set_not_s,
            fallback_occurred=False,
            fallback_reason=None,
            expectation_value=float(expectation_val),
            qpu_seconds=qpu_time,
            wall_clock_overhead_seconds=total_wall_clock,
        )

