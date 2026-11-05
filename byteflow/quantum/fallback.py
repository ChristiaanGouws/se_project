"""Automated Fallback Handling Module (UC3 & NFR Reliability)."""

import logging
from typing import Callable, Optional
from byteflow.core.graph import GraphInstance
from byteflow.quantum.executor import QuantumExecutionResult, QuantumExecutor
from byteflow.quantum.qaoa import QiskitQAOASolver
from byteflow.security.token_manager import AuthenticationError, TokenManager

logger = logging.getLogger("byteflow.quantum.fallback")


class TimeoutException(Exception):
    """Raised when IBM Quantum Cloud queue time exceeds TIMEOUT_LIMIT."""
    pass


class SimulatorMemoryExceededError(Exception):
    """Raised when graph node count exceeds local simulator RAM/qubit threshold (UC3 Alternate Flow A1)."""
    pass


class FallbackManager:
    """Wraps remote IBM Quantum execution in a fault-tolerant try/catch mechanism.

    Intercepts queue timeouts (TimeoutException) and API AuthenticationErrors, transparently
    redirecting execution to the local simulator with 'Local Sim' provenance (UC3).
    Guards simulator memory boundaries by aborting gracefully when node counts exceed safety limits.
    """

    DEFAULT_TIMEOUT_LIMIT: float = 30.0
    DEFAULT_MAX_SIMULATOR_QUBITS: int = 25

    def __init__(
        self,
        timeout_limit: float = DEFAULT_TIMEOUT_LIMIT,
        max_simulator_qubits: int = DEFAULT_MAX_SIMULATOR_QUBITS,
    ) -> None:
        self.timeout_limit = timeout_limit
        self.max_simulator_qubits = max_simulator_qubits
        self._last_fallback_notification: Optional[str] = None

    @property
    def last_fallback_notification(self) -> Optional[str]:
        return self._last_fallback_notification

    def check_simulator_boundary(self, graph: GraphInstance) -> None:
        """Boundary Condition (UC3 Alternate Flow A1): Check if graph exceeds local simulator memory limit."""
        if graph.node_count > self.max_simulator_qubits:
            raise SimulatorMemoryExceededError(
                f"Simulator memory limit exceeded: Graph has {graph.node_count} nodes, "
                f"which exceeds the local simulation threshold of {self.max_simulator_qubits} qubits. "
                f"Please reduce the graph size to {self.max_simulator_qubits} or fewer nodes to prevent memory exhaustion."
            )

    def execute_with_fallback(
        self,
        graph: GraphInstance,
        layer_depth: int = 1,
        shots: int = 1024,
        token: Optional[str] = None,
        qaoa_solver: Optional[QiskitQAOASolver] = None,
        remote_executor: Optional[Callable[..., QuantumExecutionResult]] = None,
        exact_max_cut: Optional[int] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        timeout_limit: Optional[float] = None,
    ) -> QuantumExecutionResult:
        """Execute QAOA with automated fallback to local simulation upon remote failure."""
        log = log_callback or (lambda msg: None)
        effective_timeout = timeout_limit if timeout_limit is not None else self.timeout_limit
        self._last_fallback_notification = None

        # Pre-check simulator memory boundary if graph is obviously too large for simulation
        # (Allows failing fast before dispatching or when fallback will be required)
        if graph.node_count > self.max_simulator_qubits:
            self.check_simulator_boundary(graph)

        solver = qaoa_solver or QiskitQAOASolver()

        try:
            # 1. Attempt remote execution on IBM Quantum Cloud
            if remote_executor is not None:
                # Custom/mock remote executor passed by caller/test
                log("Submitting QAOA job to remote IBM Quantum execution engine...")
                return remote_executor(
                    graph=graph,
                    layer_depth=layer_depth,
                    shots=shots,
                    token=token,
                    timeout_limit=effective_timeout,
                    log_callback=log,
                )

            # Check token validation before cloud dispatch
            is_valid_token, token_err = TokenManager.validate_token_format(token)
            if not is_valid_token:
                raise AuthenticationError(f"IBM Quantum authentication failed: {token_err}")

            # Standard cloud submission
            return solver.solve(
                graph=graph,
                layer_depth=layer_depth,
                shots=shots,
                token=token,
                exact_max_cut=exact_max_cut,
                log_callback=log,
            )

        except (TimeoutException, AuthenticationError, Exception) as exc:
            # 2. Automatically intercept failure without crashing the user session
            error_type = type(exc).__name__
            error_details = str(exc)
            fallback_msg = (
                f"[FALLBACK TRIGGERED] Remote IBM Quantum execution failed due to {error_type}: {error_details}. "
                f"Transparently redirecting QAOA circuit ansatz to local simulation engine..."
            )
            self._last_fallback_notification = fallback_msg
            log(fallback_msg)
            logger.warning(fallback_msg)

            # 3. Check simulator memory limit boundary before local simulation
            self.check_simulator_boundary(graph)

            # 4. Redirect to local simulator (Qiskit StatevectorSampler / Aer)
            executor = QuantumExecutor(timeout_seconds=effective_timeout)
            result = executor.execute_local_simulator(
                graph=graph,
                layer_depth=layer_depth,
                shots=shots,
                exact_max_cut=exact_max_cut,
                log_callback=log,
                fallback_reason=f"{error_type}: {error_details}",
            )

            log("Local simulation completed successfully with provenance ['Local Sim'].")
            return result
