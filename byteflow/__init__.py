"""ByteFlow - A Comparative Platform for Classical and Quantum Max-Cut Solutions."""

import dataclasses

# Compatibility shim: qiskit_ibm_runtime v0.49.0 defines `__dataclass_fields__` as a property
# on `BaseOptionsModel`, which triggers `AttributeError: 'property' object has no attribute 'values'`
# when inspected by Pydantic 2.12+. We patch dataclasses.is_dataclass to correctly treat classes
# with property-based __dataclass_fields__ as non-dataclasses.
_orig_is_dataclass = dataclasses.is_dataclass


def _patched_is_dataclass(obj):
    if isinstance(obj, type) and isinstance(getattr(obj, "__dataclass_fields__", None), property):
        return False
    return _orig_is_dataclass(obj)


dataclasses.is_dataclass = _patched_is_dataclass

__version__ = "1.0.0"

from byteflow.core.graph import GraphInstance, GraphPresets, GraphWorkspace
from byteflow.solvers.classical import ClassicalResult, ClassicalSolver
from byteflow.quantum.qaoa import QAOACircuitBuilder, QiskitQAOASolver
from byteflow.quantum.executor import (
    QuantumExecutionResult,
    QuantumExecutor,
    Execution_Result,
    extract_qpu_compute_time,
)
from byteflow.quantum.fallback import (
    FallbackManager,
    SimulatorMemoryExceededError,
    TimeoutException,
)
from byteflow.security.token_manager import AuthenticationError, TokenManager
from byteflow.analytics.comparative import (
    ComparativeAnalyticsEngine,
    ComparativeBenchmarkReport,
)

__all__ = [
    "GraphInstance",
    "GraphPresets",
    "GraphWorkspace",
    "ClassicalResult",
    "ClassicalSolver",
    "QAOACircuitBuilder",
    "QiskitQAOASolver",
    "QuantumExecutionResult",
    "Execution_Result",
    "extract_qpu_compute_time",
    "QuantumExecutor",
    "FallbackManager",
    "TimeoutException",
    "SimulatorMemoryExceededError",
    "TokenManager",
    "AuthenticationError",
    "ComparativeAnalyticsEngine",
    "ComparativeBenchmarkReport",
]


