"""Comparative analytics engine and ERD-compliant execution models for ByteFlow (UC5)."""

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from byteflow.core.graph import GraphInstance
from byteflow.solvers.classical import ClassicalResult
from byteflow.quantum.executor import QuantumExecutionResult


@dataclass
class ComparativeBenchmarkReport:
    """Side-by-side benchmark report comparing Classical and Quantum Max-Cut solutions (UC5)."""
    timestamp: str
    graph_name: str
    node_count: int
    edge_count: int
    exact_max_cut: Optional[int] = None

    # Completeness status & placeholder guidance (UC5 Alternate Flow A1)
    is_complete: bool = True
    placeholder_guidance: Optional[str] = None

    # Classical summary
    classical_algorithm: Optional[str] = None
    classical_cut: Optional[int] = None
    classical_cut_percentage: Optional[float] = None
    classical_approximation_ratio: Optional[float] = None
    classical_runtime_seconds: Optional[float] = None
    classical_partition_s: Optional[List[int]] = None
    classical_partition_not_s: Optional[List[int]] = None
    classical_partition_layout: Optional[Dict[int, int]] = None

    # Quantum summary
    quantum_backend: Optional[str] = None
    quantum_provenance: Optional[str] = None  # "IBM QPU" or "Local Sim"
    quantum_layer_depth: Optional[int] = None
    quantum_shots: Optional[int] = None
    quantum_cut: Optional[int] = None
    quantum_cut_percentage: Optional[float] = None
    quantum_approximation_ratio: Optional[float] = None
    quantum_max_cut_probability: Optional[float] = None
    quantum_runtime_seconds: Optional[float] = None
    quantum_qpu_seconds: Optional[float] = None
    quantum_wall_clock_overhead_seconds: Optional[float] = None
    quantum_fallback_occurred: bool = False
    quantum_fallback_reason: Optional[str] = None
    quantum_partition_s: Optional[List[int]] = None
    quantum_partition_not_s: Optional[List[int]] = None
    quantum_partition_layout: Optional[Dict[int, int]] = None
    quantum_measurement_counts: Optional[Dict[str, int]] = None

    # Comparison metrics
    approximation_ratio: Optional[float] = None  # quantum_cut / classical_cut
    cut_difference: Optional[int] = None  # quantum_cut - classical_cut
    speedup_ratio: Optional[float] = None
    quantum_matched_classical: bool = False
    quantum_exceeded_classical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def generate_ascii_summary(self) -> str:
        """Render a clean side-by-side ASCII comparison card."""
        sep = "=" * 76
        sub_sep = "-" * 76

        if not self.is_complete:
            lines = [
                sep,
                " BYTEFLOW COMPARATIVE MAX-CUT ANALYTICS (INCOMPLETE STATE - UC5 A1)",
                sep,
                f" Graph: {self.graph_name} | Vertices: {self.node_count} | Edges: {self.edge_count}",
                sub_sep,
                f" Status: Incomplete Data",
                f" Guidance: {self.placeholder_guidance}",
                sep,
            ]
            return "\n".join(lines)

        if self.quantum_qpu_seconds is not None:
            quantum_runtime_display = f"{self.quantum_qpu_seconds*1000.0:.2f} ms (QPU)"
        elif self.quantum_runtime_seconds is not None:
            quantum_runtime_display = (
                f"{self.quantum_runtime_seconds*1000.0:.2f} ms"
                if self.quantum_runtime_seconds < 1.0
                else f"{self.quantum_runtime_seconds:.3f} s"
            )
        else:
            quantum_runtime_display = "N/A"

        lines = [
            sep,
            f" BYTEFLOW COMPARATIVE MAX-CUT ANALYTICS BENCHMARK (UC5)",
            sep,
            f" Graph: {self.graph_name} | Vertices: {self.node_count} | Edges: {self.edge_count}",
            f" Ground Truth Optimum Max-Cut: {self.exact_max_cut if self.exact_max_cut is not None else 'N/A'}",
            sub_sep,
            f" {'METRIC':<28} | {'CLASSICAL (' + (self.classical_algorithm or '')[:10] + ')':<20} | {'QUANTUM (' + (self.quantum_provenance or '') + ')':<20}",
            sub_sep,
            f" {'Cut Value':<28} | {f'{self.classical_cut}/{self.edge_count}':<20} | {f'{self.quantum_cut}/{self.edge_count}':<20}",
            f" {'Cut Percentage':<28} | {f'{self.classical_cut_percentage:.1f}%' if self.classical_cut_percentage is not None else 'N/A':<20} | {f'{self.quantum_cut_percentage:.1f}%' if self.quantum_cut_percentage is not None else 'N/A':<20}",
            f" {'Approximation Ratio':<28} | {f'{self.classical_approximation_ratio:.4f}' if self.classical_approximation_ratio is not None else 'N/A':<20} | {f'{self.quantum_approximation_ratio:.4f}' if self.quantum_approximation_ratio is not None else 'N/A':<20}",
            f" {'Execution Runtime':<28} | {f'{(self.classical_runtime_seconds or 0)*1000:.2f} ms':<20} | {quantum_runtime_display:<20}",
        ]

        if self.quantum_qpu_seconds is not None:
            lines.append(
                f" {'Active QPU Compute Time':<28} | {'N/A':<20} | {f'{self.quantum_qpu_seconds*1000.0:.2f} ms ({self.quantum_qpu_seconds:.4f} s)':<20}"
            )
            if self.quantum_wall_clock_overhead_seconds is not None:
                lines.append(
                    f" {'Cloud Queue/Wait Time':<28} | {'N/A':<20} | {f'{self.quantum_wall_clock_overhead_seconds:.2f} s':<20}"
                )

        lines.extend([
            f" {'Max-Cut Sample Prob':<28} | {'100.0% (deterministic)':<20} | {f'{self.quantum_max_cut_probability:.1f}% ({self.quantum_shots} shots)' if self.quantum_max_cut_probability is not None else 'N/A':<20}",
            f" {'Provenance':<28} | {'Local CPU':<20} | {f'{self.quantum_provenance} ({self.quantum_backend})':<20}",
            sub_sep,
            f" Summary: Quantum {'exceeded' if self.quantum_exceeded_classical else 'matched' if self.quantum_matched_classical else 'underperformed'} classical cut by {self.cut_difference} edges.",
            f" Fallback Status: {'TRIGGERED (' + (self.quantum_fallback_reason or '') + ')' if self.quantum_fallback_occurred else 'None (Clean Execution)'}",
            sep,
        ])
        return "\n".join(lines)


class ComparativeAnalyticsEngine:
    """Analyzes and compiles results from classical and quantum solvers into side-by-side benchmarks."""

    @staticmethod
    def compare(
        graph: GraphInstance,
        classical_result: Optional[ClassicalResult] = None,
        quantum_result: Optional[QuantumExecutionResult] = None,
        layer_depth: int = 1,
        exact_max_cut: Optional[int] = None,
    ) -> ComparativeBenchmarkReport:
        """Generate a complete or partial ComparativeBenchmarkReport per UC5 and Alternate Flow A1."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Alternate Flow A1: Incomplete solver data handling
        if classical_result is None and quantum_result is None:
            return ComparativeBenchmarkReport(
                timestamp=timestamp,
                graph_name=graph.name,
                node_count=graph.node_count,
                edge_count=graph.edge_count,
                exact_max_cut=exact_max_cut,
                is_complete=False,
                placeholder_guidance=(
                    "Incomplete solver data: Neither classical nor quantum solver has been executed yet. "
                    "Please run both solvers on the active graph to view comparative benchmarking metrics."
                ),
            )

        if classical_result is not None and quantum_result is None:
            return ComparativeBenchmarkReport(
                timestamp=timestamp,
                graph_name=graph.name,
                node_count=graph.node_count,
                edge_count=graph.edge_count,
                exact_max_cut=exact_max_cut,
                is_complete=False,
                placeholder_guidance=(
                    "Incomplete solver data: Quantum QAOA solver has not been executed yet. "
                    "Please execute the quantum solver to enable side-by-side comparative benchmarking."
                ),
                classical_algorithm=classical_result.algorithm_name,
                classical_cut=classical_result.cut_value,
                classical_cut_percentage=classical_result.cut_percentage,
                classical_approximation_ratio=classical_result.approximation_ratio,
                classical_runtime_seconds=classical_result.execution_time_seconds,
                classical_partition_s=classical_result.set_s,
                classical_partition_not_s=classical_result.set_not_s,
                classical_partition_layout=classical_result.partition_layout,
            )

        if classical_result is None and quantum_result is not None:
            return ComparativeBenchmarkReport(
                timestamp=timestamp,
                graph_name=graph.name,
                node_count=graph.node_count,
                edge_count=graph.edge_count,
                exact_max_cut=exact_max_cut,
                is_complete=False,
                placeholder_guidance=(
                    "Incomplete solver data: Classical baseline solver has not been executed yet. "
                    "Please execute the classical solver to enable side-by-side comparative benchmarking."
                ),
                quantum_backend=quantum_result.backend_name,
                quantum_provenance=quantum_result.provenance_label,
                quantum_layer_depth=layer_depth,
                quantum_shots=quantum_result.shots,
                quantum_cut=quantum_result.cut_value,
                quantum_cut_percentage=quantum_result.cut_percentage,
                quantum_approximation_ratio=quantum_result.approximation_ratio,
                quantum_max_cut_probability=quantum_result.best_cut_probability,
                quantum_runtime_seconds=quantum_result.execution_time_seconds,
                quantum_qpu_seconds=quantum_result.qpu_seconds,
                quantum_wall_clock_overhead_seconds=quantum_result.wall_clock_overhead_seconds,
                quantum_fallback_occurred=quantum_result.fallback_occurred,
                quantum_fallback_reason=quantum_result.fallback_reason,
                quantum_partition_s=quantum_result.set_s,
                quantum_partition_not_s=quantum_result.set_not_s,
                quantum_partition_layout=quantum_result.partition_layout,
                quantum_measurement_counts=quantum_result.measurement_counts,
            )

        # Main Flow: Both solvers have completed
        cut_diff = quantum_result.cut_value - classical_result.cut_value
        matched = quantum_result.cut_value == classical_result.cut_value
        exceeded = quantum_result.cut_value > classical_result.cut_value

        speedup = (
            classical_result.execution_time_seconds / quantum_result.execution_time_seconds
            if quantum_result.execution_time_seconds > 0
            else 0.0
        )

        # Comparative approximation ratio: quantum cut / classical cut
        if classical_result.cut_value > 0:
            comp_approx_ratio = min(1.0, max(0.0, quantum_result.cut_value / classical_result.cut_value))
        else:
            comp_approx_ratio = 1.0

        return ComparativeBenchmarkReport(
            timestamp=timestamp,
            graph_name=graph.name,
            node_count=graph.node_count,
            edge_count=graph.edge_count,
            exact_max_cut=exact_max_cut,
            is_complete=True,
            placeholder_guidance=None,
            classical_algorithm=classical_result.algorithm_name,
            classical_cut=classical_result.cut_value,
            classical_cut_percentage=classical_result.cut_percentage,
            classical_approximation_ratio=classical_result.approximation_ratio,
            classical_runtime_seconds=classical_result.execution_time_seconds,
            classical_partition_s=classical_result.set_s,
            classical_partition_not_s=classical_result.set_not_s,
            classical_partition_layout=classical_result.partition_layout,
            quantum_backend=quantum_result.backend_name,
            quantum_provenance=quantum_result.provenance_label,
            quantum_layer_depth=layer_depth,
            quantum_shots=quantum_result.shots,
            quantum_cut=quantum_result.cut_value,
            quantum_cut_percentage=quantum_result.cut_percentage,
            quantum_approximation_ratio=quantum_result.approximation_ratio,
            quantum_max_cut_probability=quantum_result.best_cut_probability,
            quantum_runtime_seconds=quantum_result.execution_time_seconds,
            quantum_qpu_seconds=quantum_result.qpu_seconds,
            quantum_wall_clock_overhead_seconds=quantum_result.wall_clock_overhead_seconds,
            quantum_fallback_occurred=quantum_result.fallback_occurred,
            quantum_fallback_reason=quantum_result.fallback_reason,
            quantum_partition_s=quantum_result.set_s,
            quantum_partition_not_s=quantum_result.set_not_s,
            quantum_partition_layout=quantum_result.partition_layout,
            quantum_measurement_counts=quantum_result.measurement_counts,
            approximation_ratio=comp_approx_ratio,
            cut_difference=cut_diff,
            speedup_ratio=speedup,
            quantum_matched_classical=matched,
            quantum_exceeded_classical=exceeded,
        )

