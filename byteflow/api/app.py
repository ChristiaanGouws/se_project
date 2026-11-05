"""REST API Controller and endpoints for ByteFlow Virtual Laboratory."""

from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from byteflow.analytics.comparative import (
    ComparativeAnalyticsEngine,
    ComparativeBenchmarkReport,
)
from byteflow.core.graph import GraphInstance, GraphPresets, GraphWorkspace
from byteflow.quantum.executor import QuantumExecutionResult
from byteflow.quantum.fallback import (
    FallbackManager,
    SimulatorMemoryExceededError,
    TimeoutException,
)
from byteflow.quantum.qaoa import QiskitQAOASolver
from byteflow.security.token_manager import AuthenticationError, TokenManager
from byteflow.solvers.classical import ClassicalResult, ClassicalSolver

app = FastAPI(
    title="ByteFlow API",
    description="RESTful endpoints for Classical and Quantum Max-Cut evaluations and comparative benchmarking.",
    version="1.0.0",
)

# Persistent singleton workspace and session services
workspace = GraphWorkspace()
token_manager = TokenManager()
fallback_manager = FallbackManager()

# Results cache keyed by graph name
cached_classical_results: Dict[str, ClassicalResult] = {}
cached_quantum_results: Dict[str, QuantumExecutionResult] = {}


class ClassicalSolveRequest(BaseModel):
    graph_id: Optional[str] = Field(None, description="Preset name of predefined graph")
    adjacency_matrix: Optional[List[List[int]]] = Field(None, description="Custom adjacency matrix")
    graph: Optional[Dict[str, Any]] = Field(None, description="Graph dictionary structure")
    method: str = Field("auto", description="'exact', 'greedy', or 'auto'")


class QuantumSolveRequest(BaseModel):
    graph_id: Optional[str] = Field(None, description="Preset name of predefined graph")
    layer_depth: int = Field(1, ge=1, le=10, description="QAOA layer depth p")
    p: Optional[int] = Field(None, ge=1, le=10, description="Alias for layer_depth")
    shots: int = Field(1024, ge=1, le=100000, description="Measurement shots")
    token: Optional[str] = Field(None, description="IBM Quantum API token")
    timeout_limit: Optional[float] = Field(None, description="Queue timeout limit in seconds")


class TokenConfigRequest(BaseModel):
    token: Optional[str] = Field(None, description="IBM Quantum API token to validate and encrypt")


class ViewToggleRequest(BaseModel):
    mode: Optional[str] = Field(None, description="'dual', 'classical_only', or 'quantum_only'")


def resolve_graph(
    graph_id: Optional[str] = None,
    adjacency_matrix: Optional[List[List[int]]] = None,
    graph_payload: Optional[Dict[str, Any]] = None,
) -> GraphInstance:
    """Helper to resolve a GraphInstance from various input formats."""
    if adjacency_matrix is not None:
        try:
            return GraphInstance.from_adjacency_matrix("Custom Graph", adjacency_matrix)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid adjacency matrix: {str(e)}",
            )

    if graph_payload is not None:
        try:
            if "adjacency_matrix" in graph_payload:
                return GraphInstance.from_adjacency_matrix(
                    graph_payload.get("name", "Custom Graph"),
                    graph_payload["adjacency_matrix"],
                )
            return GraphInstance(
                name=graph_payload.get("name", "Custom Graph"),
                node_count=graph_payload["node_count"],
                edges=tuple(tuple(e) for e in graph_payload["edges"]),
                description=graph_payload.get("description", ""),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid graph payload: {str(e)}",
            )

    if graph_id is not None:
        presets = GraphPresets.all_presets()
        if graph_id not in presets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Graph preset '{graph_id}' not found. Available presets: {list(presets.keys())}",
            )
        return presets[graph_id]

    return workspace.active_graph


@app.post("/api/solve/classical")
def solve_classical(req: ClassicalSolveRequest = ClassicalSolveRequest()):
    """Execute classical Max-Cut solver (UC1)."""
    try:
        # Check for malformed / empty graph explicitly
        if req.adjacency_matrix is not None and len(req.adjacency_matrix) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed/empty graph input: Adjacency matrix cannot be empty.",
            )

        target_graph = resolve_graph(req.graph_id, req.adjacency_matrix, req.graph)
        result = ClassicalSolver.solve(target_graph, method=req.method)
        cached_classical_results[target_graph.name] = result

        return {
            "status": "success",
            "optimal_cut_value": result.optimal_cut_value,
            "cut_value": result.cut_value,
            "partition_layout": result.partition_layout,
            "wall_clock_runtime": result.wall_clock_runtime,
            "execution_time_seconds": result.execution_time_seconds,
            "best_bitstring": result.best_bitstring,
            "approximation_ratio": result.approximation_ratio,
            "algorithm_name": result.algorithm_name,
            "set_s": result.set_s,
            "set_not_s": result.set_not_s,
            "total_edges": result.total_edges,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classical execution failed: {str(e)}",
        )


@app.post("/api/solve/quantum")
def solve_quantum(req: QuantumSolveRequest = QuantumSolveRequest()):
    """Execute Quantum QAOA solver wrapped by FallbackManager (UC2, UC3)."""
    try:
        target_graph = resolve_graph(req.graph_id)
        effective_depth = req.p if req.p is not None else req.layer_depth

        # Use token from request or active session
        session_token = req.token or token_manager.get_session_token()

        # Run via FallbackManager
        result = fallback_manager.execute_with_fallback(
            graph=target_graph,
            layer_depth=effective_depth,
            shots=req.shots,
            token=session_token,
            timeout_limit=req.timeout_limit,
        )

        cached_quantum_results[target_graph.name] = result

        return {
            "status": "success",
            "provenance_label": result.provenance_label,
            "backend_name": result.backend_name,
            "cut_value": result.cut_value,
            "optimal_cut_value": result.optimal_cut_value,
            "expectation_value": result.expectation_value,
            "partition_layout": result.partition_layout,
            "best_bitstring": result.best_bitstring,
            "measurement_counts": result.measurement_counts,
            "shots": result.shots,
            "wall_clock_runtime": result.wall_clock_runtime,
            "execution_time_seconds": result.execution_time_seconds,
            "qpu_seconds": result.qpu_seconds,
            "wall_clock_overhead_seconds": result.wall_clock_overhead_seconds,
            "approximation_ratio": result.approximation_ratio,
            "best_cut_probability": result.best_cut_probability,
            "fallback_occurred": result.fallback_occurred,
            "fallback_reason": result.fallback_reason,
            "set_s": result.set_s,
            "set_not_s": result.set_not_s,
        }
    except SimulatorMemoryExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quantum execution error: {str(e)}",
        )


@app.get("/api/comparative")
def get_comparative_analytics(graph_id: Optional[str] = None):
    """Retrieve comparative analytics report for the specified or active graph (UC5)."""
    target_graph = resolve_graph(graph_id)
    classical_res = cached_classical_results.get(target_graph.name)
    quantum_res = cached_quantum_results.get(target_graph.name)

    report = ComparativeAnalyticsEngine.compare(
        graph=target_graph,
        classical_result=classical_res,
        quantum_result=quantum_res,
        exact_max_cut=classical_res.cut_value if classical_res and classical_res.algorithm_name == "Exact Brute-Force" else None,
    )

    return report.to_dict()


@app.post("/api/token/validate")
def validate_token(req: TokenConfigRequest):
    """Validate and configure IBM Quantum API token (UC4)."""
    result = token_manager.configure_token(req.token)
    if not result.get("authenticated", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error", "Invalid API token."),
        )
    return result


@app.get("/api/workspace")
def get_workspace():
    """Retrieve current workspace state, active graph, and presets."""
    return {
        "active_graph": {
            "name": workspace.active_graph.name,
            "node_count": workspace.active_graph.node_count,
            "edge_count": workspace.active_graph.edge_count,
            "description": workspace.active_graph.description,
            "nodes": workspace.node_list,
            "adjacency_matrix": workspace.adjacency_matrix,
        },
        "view_mode": workspace.view_mode,
        "available_presets": list(workspace.presets.keys()),
    }


@app.post("/api/workspace/reset")
def reset_workspace():
    """Reset workspace to default graph preset (4-Node Diamond) and dual view."""
    workspace.reset_workspace()
    return get_workspace()


@app.post("/api/workspace/randomise")
def randomise_workspace():
    """Select a random predefined graph preset."""
    workspace.randomise_graph()
    return get_workspace()


@app.post("/api/workspace/toggle_view")
def toggle_view(req: ViewToggleRequest = ViewToggleRequest()):
    """Toggle between 'dual', 'classical_only', and 'quantum_only'."""
    try:
        new_mode = workspace.toggle_view(req.mode)
        return {"status": "success", "view_mode": new_mode}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
