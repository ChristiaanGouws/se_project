"""Quantum execution models, IBM Cloud runner, and local simulator fallback engine."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


from qiskit.primitives import StatevectorSampler

from byteflow.core.graph import GraphInstance
from byteflow.quantum.qaoa import QAOACircuitBuilder

logger = logging.getLogger("byteflow.quantum.executor")


@dataclass(frozen=True)
class QuantumExecutionResult:
    """Standardized result returned by quantum execution (remote or fallback)."""
    provenance_label: str  # "IBM QPU" or "Local Sim"
    backend_name: str
    shots: int
    best_bitstring: str
    cut_value: int
    total_edges: int
    approximation_ratio: float
    best_cut_probability: float  # Percentage of shots achieving max cut
    execution_time_seconds: float
    measurement_counts: Dict[str, int]
    cut_histogram: Dict[int, int]
    set_s: List[int]
    set_not_s: List[int]
    fallback_occurred: bool
    fallback_reason: Optional[str] = None
    expectation_value: float = 0.0
    qpu_seconds: Optional[float] = None
    wall_clock_overhead_seconds: Optional[float] = None

    @property
    def optimal_cut_value(self) -> int:
        return self.cut_value

    @property
    def wall_clock_runtime(self) -> float:
        """Active execution runtime (true QPU compute time when available, else simulation runtime)."""
        return self.execution_time_seconds

    @property
    def partition_layout(self) -> Dict[int, int]:
        return {i: int(b) for i, b in enumerate(self.best_bitstring)}

    @property
    def cut_percentage(self) -> float:
        return (self.cut_value / self.total_edges * 100.0) if self.total_edges > 0 else 0.0

    @property
    def formatted_runtime(self) -> str:
        """Format active compute runtime cleanly in milliseconds or seconds for fair CPU comparison."""
        if self.qpu_seconds is not None:
            return f"{self.qpu_seconds * 1000.0:.2f} ms ({self.qpu_seconds:.4f} s)"
        if self.execution_time_seconds < 1.0:
            return f"{self.execution_time_seconds * 1000.0:.2f} ms"
        return f"{self.execution_time_seconds:.3f} s"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provenance_label": self.provenance_label,
            "backend_name": self.backend_name,
            "shots": self.shots,
            "best_bitstring": self.best_bitstring,
            "cut_value": self.cut_value,
            "optimal_cut_value": self.optimal_cut_value,
            "expectation_value": self.expectation_value,
            "total_edges": self.total_edges,
            "approximation_ratio": self.approximation_ratio,
            "best_cut_probability": self.best_cut_probability,
            "execution_time_seconds": self.execution_time_seconds,
            "wall_clock_runtime": self.wall_clock_runtime,
            "qpu_seconds": self.qpu_seconds,
            "wall_clock_overhead_seconds": self.wall_clock_overhead_seconds,
            "formatted_runtime": self.formatted_runtime,
            "partition_layout": self.partition_layout,
            "measurement_counts": self.measurement_counts,
            "cut_histogram": self.cut_histogram,
            "set_s": self.set_s,
            "set_not_s": self.set_not_s,
            "fallback_occurred": self.fallback_occurred,
            "fallback_reason": self.fallback_reason,
            "cut_percentage": self.cut_percentage,
        }


# Canonical alias for Execution_Result
Execution_Result = QuantumExecutionResult


def extract_qpu_compute_time(job: Any) -> Optional[float]:
    """Query native job telemetry from Qiskit job to extract true active QPU compute time in seconds.

    Extracts quantum_seconds from job.metrics().get('usage', {}), or falls back to job.usage().
    """
    if job is None:
        return None

    # Step 1: Query job.metrics().get("usage", {})
    try:
        if hasattr(job, "metrics") and callable(getattr(job, "metrics")):
            metrics = job.metrics()
            if isinstance(metrics, dict):
                usage = metrics.get("usage", {})
                if isinstance(usage, dict):
                    for key in ("quantum_seconds", "qpu_charge_time_seconds", "seconds"):
                        val = usage.get(key)
                        if val is not None and isinstance(val, (int, float)):
                            return float(val)
                elif isinstance(usage, (int, float)):
                    return float(usage)
    except Exception as exc:
        logger.debug("Telemetry query job.metrics() encountered: %s", exc)

    # Step 2: Fall back to job.usage()
    try:
        if hasattr(job, "usage") and callable(getattr(job, "usage")):
            usage_val = job.usage()
            if isinstance(usage_val, (int, float)):
                return float(usage_val)
            elif isinstance(usage_val, dict):
                for key in ("quantum_seconds", "qpu_charge_time_seconds", "seconds"):
                    val = usage_val.get(key)
                    if val is not None and isinstance(val, (int, float)):
                        return float(val)
    except Exception as exc:
        logger.debug("Telemetry query job.usage() encountered: %s", exc)

    return None


def extract_counts_from_pub_result(pub_result) -> Dict[str, int]:
    """Helper to extract count dictionary from Qiskit V2 Primitive result."""
    data_bin = getattr(pub_result, "data", pub_result)
    # Direct dictionary format if already dict
    if isinstance(data_bin, dict):
        return data_bin


    # Qiskit 1.x/2.x data bins typically name classical registers 'c' or 'meas'
    for attr in ("c", "meas"):
        if hasattr(data_bin, attr):
            bit_array = getattr(data_bin, attr)
            if hasattr(bit_array, "get_counts"):
                return bit_array.get_counts()

    # Generic search over data_bin fields
    if hasattr(data_bin, "keys") and callable(getattr(data_bin, "keys")):
        for key in data_bin.keys():
            item = getattr(data_bin, key, None)
            if item is not None and hasattr(item, "get_counts"):
                return item.get_counts()

    raise ValueError(f"Unable to extract measurement counts from data bin: {data_bin}")



class QuantumExecutor:
    """Manages quantum circuit execution with fault-tolerant automated fallback.

    Implements User Model UC2 (Quantum Execution) and UC3 (Fallback Handling Module):
    1. Attempts execution on IBM Quantum Cloud hardware using Qiskit Runtime Sampler.
    2. If token is invalid, queue hangs, or hardware is unreachable, automatically
       diverts to the local StatevectorSampler.
    3. Accurately labels provenance ('IBM QPU' vs 'Local Sim').
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds

    def execute_local_simulator(
        self,
        graph: GraphInstance,
        layer_depth: int = 1,
        gamma: Optional[float] = None,
        beta: Optional[float] = None,
        shots: int = 1024,
        exact_max_cut: Optional[int] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        fallback_reason: Optional[str] = None,
    ) -> QuantumExecutionResult:
        """Run QAOA using local statevector simulation."""
        log = log_callback or (lambda msg: None)
        log("Executing QAOA on Local Simulator (StatevectorSampler)...")
        start_time = time.perf_counter()

        circuit = QAOACircuitBuilder.build_circuit(
            graph=graph,
            layer_depth=layer_depth,
            gamma=gamma,
            beta=beta,
        )

        sampler = StatevectorSampler()
        job = sampler.run([circuit], shots=shots)
        result = job.result()
        raw_counts = extract_counts_from_pub_result(result[0])
        elapsed = time.perf_counter() - start_time

        return self._process_measurement_results(
            graph=graph,
            raw_counts=raw_counts,
            shots=shots,
            elapsed_time=elapsed,
            provenance="Local Sim",
            backend_name="qiskit.primitives.StatevectorSampler",
            exact_max_cut=exact_max_cut,
            fallback_occurred=(fallback_reason is not None),
            fallback_reason=fallback_reason,
            log=log,
            qpu_seconds=None,
            wall_clock_overhead_seconds=elapsed,
        )

    def execute_with_fallback(
        self,
        graph: GraphInstance,
        layer_depth: int = 1,
        gamma: Optional[float] = None,
        beta: Optional[float] = None,
        shots: int = 1024,
        api_token: Optional[str] = None,
        exact_max_cut: Optional[int] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> QuantumExecutionResult:
        """Attempt execution on IBM Quantum Cloud; fallback to local simulation upon error."""
        log = log_callback or (lambda msg: None)
        effective_timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds

        # Check if API token is provided
        if not api_token or not api_token.strip():
            log("No IBM Quantum API token provided. Activating Fallback Module (UC3)...")
            return self.execute_local_simulator(
                graph=graph,
                layer_depth=layer_depth,
                gamma=gamma,
                beta=beta,
                shots=shots,
                exact_max_cut=exact_max_cut,
                log_callback=log,
                fallback_reason="No IBM Quantum API token configured.",
            )

        log(f"Initiating IBM Quantum Cloud Session (Token: {api_token[:4]}***)...")
        start_time = time.perf_counter()

        try:
            # Dynamic import to isolate dependency failures
            from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as RemoteSampler
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

            service = QiskitRuntimeService(token=api_token.strip())
            log("Searching for operational IBM Quantum QPU...")
            backend = service.least_busy(
                simulator=False,
                operational=True,
                min_num_qubits=graph.node_count,
            )
            log(f"Selected IBM Processor: {backend.name}")

            circuit = QAOACircuitBuilder.build_circuit(
                graph=graph,
                layer_depth=layer_depth,
                gamma=gamma,
                beta=beta,
            )
            log("Transpiling QAOA ansatz for target QPU instruction set architecture (ISA)...")
            pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=1)
            isa_circuit = pass_manager.run(circuit)

            log(f"Submitting {shots} shots to {backend.name} queue...")
            sampler = RemoteSampler(mode=backend)
            job = sampler.run([isa_circuit], shots=shots)

            # Polling with timeout
            poll_interval = 3.0
            accumulated_wait = 0.0
            log("Awaiting hardware results from IBM Quantum Cloud...")

            while not job.done():
                time.sleep(poll_interval)
                accumulated_wait += poll_interval
                status = job.status()
                log(f"Queue Status: {status} (Waited {accumulated_wait:.1f}s)")
                if accumulated_wait >= effective_timeout:
                    raise TimeoutError(
                        f"IBM queue wait exceeded safety timeout limit ({effective_timeout:.1f}s)."
                    )

            result = job.result()
            raw_counts = extract_counts_from_pub_result(result[0])
            elapsed_wall_clock = time.perf_counter() - start_time

            # Query native QPU telemetry: extract true active QPU hardware compute time
            qpu_time = extract_qpu_compute_time(job)
            if qpu_time is not None:
                log(
                    f"Extracted true active QPU compute time: {qpu_time * 1000.0:.2f} ms "
                    f"({qpu_time:.4f} s) [Hardware queue + network latency: {elapsed_wall_clock:.2f} s]"
                )
                active_runtime = qpu_time
            else:
                log(f"Remote IBM execution completed in {elapsed_wall_clock:.2f} s (QPU usage metrics not reported).")
                active_runtime = elapsed_wall_clock

            return self._process_measurement_results(
                graph=graph,
                raw_counts=raw_counts,
                shots=shots,
                elapsed_time=active_runtime,
                provenance="IBM QPU",
                backend_name=backend.name,
                exact_max_cut=exact_max_cut,
                fallback_occurred=False,
                fallback_reason=None,
                log=log,
                qpu_seconds=qpu_time,
                wall_clock_overhead_seconds=elapsed_wall_clock,
            )

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            log(f"[WARNING] IBM Quantum remote execution failed: {error_msg}")
            log("Engaging Fallback Handling Module (UC3) -> Redirecting to Local Simulation...")

            return self.execute_local_simulator(
                graph=graph,
                layer_depth=layer_depth,
                gamma=gamma,
                beta=beta,
                shots=shots,
                exact_max_cut=exact_max_cut,
                log_callback=log,
                fallback_reason=error_msg,
            )

    def _process_measurement_results(
        self,
        graph: GraphInstance,
        raw_counts: Dict[str, int],
        shots: int,
        elapsed_time: float,
        provenance: str,
        backend_name: str,
        exact_max_cut: Optional[int],
        fallback_occurred: bool,
        fallback_reason: Optional[str],
        log: Callable[[str], None],
        qpu_seconds: Optional[float] = None,
        wall_clock_overhead_seconds: Optional[float] = None,
    ) -> QuantumExecutionResult:
        """Process raw measured bitstrings into partition metrics."""
        # Qiskit bitstrings are often little-endian (qubit 0 is rightmost bit).
        # We normalize bitstrings such that bit i corresponds to vertex i.
        cut_histogram: Dict[int, int] = {}
        transformed_counts: Dict[str, int] = {}

        for raw_bits, frequency in raw_counts.items():
            # Vertex i corresponds to qubit index i: reverse bitstring for standard indexing
            partition_str = raw_bits[::-1]
            transformed_counts[partition_str] = frequency
            cut = graph.cut_value(partition_str)
            cut_histogram[cut] = cut_histogram.get(cut, 0) + frequency

        best_cut = max(cut_histogram.keys())
        shots_with_best_cut = cut_histogram[best_cut]
        best_cut_probability = (shots_with_best_cut / shots) * 100.0

        # Find the most frequent bitstring that achieves the best cut
        candidate_bitstrings = {
            b: freq for b, freq in transformed_counts.items() if graph.cut_value(b) == best_cut
        }
        winning_bitstring = max(candidate_bitstrings.items(), key=lambda item: item[1])[0]

        set_s, set_not_s = graph.partition_sets(winning_bitstring)
        approx_ratio = (best_cut / exact_max_cut) if exact_max_cut else (best_cut / graph.edge_count)

        log(f"Execution complete. Best cut: {best_cut}/{graph.edge_count} ({best_cut_probability:.1f}% of shots).")
        if qpu_seconds is not None:
            log(
                f"Active QPU hardware compute time: {qpu_seconds * 1000.0:.2f} ms "
                f"({qpu_seconds:.4f} s) [Hardware queue + network latency: {wall_clock_overhead_seconds:.2f} s]"
            )
        else:
            log(
                f"Execution runtime: {elapsed_time * 1000.0:.2f} ms"
                if elapsed_time < 1.0
                else f"Execution runtime: {elapsed_time:.3f} s"
            )
        log(f"Provenance: [{provenance}] on {backend_name}")

        total_shots_counted = sum(transformed_counts.values()) or shots
        expectation_val = (
            sum(cut * count for cut, count in cut_histogram.items()) / total_shots_counted
            if total_shots_counted > 0
            else 0.0
        )

        return QuantumExecutionResult(
            provenance_label=provenance,
            backend_name=backend_name,
            shots=shots,
            best_bitstring=winning_bitstring,
            cut_value=best_cut,
            total_edges=graph.edge_count,
            approximation_ratio=min(1.0, approx_ratio),
            best_cut_probability=best_cut_probability,
            execution_time_seconds=elapsed_time,
            measurement_counts=transformed_counts,
            cut_histogram=cut_histogram,
            set_s=set_s,
            set_not_s=set_not_s,
            fallback_occurred=fallback_occurred,
            fallback_reason=fallback_reason,
            expectation_value=float(expectation_val),
            qpu_seconds=qpu_seconds,
            wall_clock_overhead_seconds=wall_clock_overhead_seconds,
        )
