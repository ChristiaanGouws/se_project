"""ByteFlow Virtual Laboratory User Interface (Tkinter dashboard implementation).

Refactored into a tabular, high-density dashboard UI with:
1. Global theme engine with WCAG AA compliance and no white borders.
2. Two-column responsive layout (fixed 320px setup column, stretching results area).
3. Grouped setup cards with plain text button labels and aligned inputs.
4. Channel cards with compact canvases and 2-column key/value Treeviews.
5. Benchmark comparison table with deltas and color-coded status tags.
6. Execution history table with column click-to-sort and CSV export.
7. Telemetry & provenance log with level tags and TXT export.
8. Status bar with progress feedback and live elapsed timer.
9. Fully thread-safe UI updates via queue and polling.
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Tuple

from byteflow.analytics.comparative import (
    ComparativeAnalyticsEngine,
    ComparativeBenchmarkReport,
)
from byteflow.core.graph import GraphInstance, GraphPresets, GraphWorkspace
from byteflow.quantum.executor import QuantumExecutionResult, QuantumExecutor
from byteflow.quantum.fallback import FallbackManager
from byteflow.security.token_manager import TokenManager
from byteflow.solvers.classical import ClassicalResult, ClassicalSolver
from byteflow.ui.benchmark_table import BenchmarkTable
from byteflow.ui.canvas import GraphVisualizerCanvas
from byteflow.ui.channel_card import ChannelCard
from byteflow.ui.history_table import HistoryTable
from byteflow.ui.setup_panel import SetupPanel
from byteflow.ui.status_bar import StatusBar
from byteflow.ui.theme import (
    BG_APP,
    BG_CARD,
    BORDER_SUBTLE,
    FONT_SUBHEADER,
    FONT_TITLE,
    apply_theme,
)


class ByteFlowApp(tk.Tk):
    """The central ByteFlow Virtual Laboratory application."""

    def __init__(self) -> None:
        super().__init__()
        self.title("ByteFlow - Comparative Classical & Quantum Max-Cut Laboratory")
        self.geometry("1260x860")
        self.minsize(1060, 720)

        # 1. Apply centralized dark styling
        self.style = apply_theme(self)

        # 2. State models
        self.workspace = GraphWorkspace()
        self.presets = self.workspace.presets
        self.current_graph: GraphInstance = self.workspace.active_graph
        self.fallback_manager = FallbackManager()
        self.token_manager = TokenManager()
        self.executor = QuantumExecutor(timeout_seconds=30.0)

        self.classical_result: Optional[ClassicalResult] = None
        self.quantum_result: Optional[QuantumExecutionResult] = None
        self.latest_report: Optional[ComparativeBenchmarkReport] = None

        # Thread-safe UI dispatch queue
        self._ui_queue: queue.Queue = queue.Queue()
        self.after(50, self._process_ui_queue)

        # 3. Build UI Layout
        self._build_ui()

        # Initialize default graph state
        self._on_preset_change("4-Node Diamond")
        self.log("OK", "ByteFlow Virtual Laboratory initialized and ready.")

    def _process_ui_queue(self) -> None:
        """Poll queued UI invocations dispatched from background worker threads."""
        try:
            while True:
                fn, args, kwargs = self._ui_queue.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception as exc:
                    self.log("ERROR", f"UI dispatch error: {exc}")
                finally:
                    self._ui_queue.task_done()
        except queue.Empty:
            pass
        self.after(50, self._process_ui_queue)

    def _dispatch_to_ui(self, fn, *args, **kwargs) -> None:
        """Enqueue a callable to be safely executed on Tkinter's main UI thread."""
        self._ui_queue.put((fn, args, kwargs))

    def _build_ui(self) -> None:
        """Assemble the two-column dashboard structure."""
        # Top Header Stage
        header = ttk.Frame(self, padding=(24, 14, 24, 8))
        header.pack(fill="x")

        ttk.Label(
            header,
            text="BYTEFLOW: VIRTUAL MAX-CUT LABORATORY",
            style="Header.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Interactive Benchmarking & Usability Platform for Classical vs. Quantum QAOA Optimisation",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        # Main Workspace: 2-column Grid Layout
        workspace = ttk.Frame(self, padding=(24, 6, 24, 8))
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=0, minsize=330)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        # --------------------------------------------------------------------
        # Left Setup Panel
        # --------------------------------------------------------------------
        self.setup_panel = SetupPanel(
            workspace,
            preset_names=list(self.presets.keys()),
            on_preset_change=self._on_preset_change,
            on_reset=self._reset_workspace,
            on_randomise=self._randomise_graph,
            on_toggle_view=self._toggle_view,
            on_run_classical=self._start_classical_thread,
            on_run_quantum=self._start_quantum_thread,
            on_run_benchmark=self._start_benchmark_thread,
        )
        self.setup_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        # --------------------------------------------------------------------
        # Right Results Panel
        # --------------------------------------------------------------------
        self.results_panel = ttk.Frame(workspace, style="TFrame")
        self.results_panel.grid(row=0, column=1, sticky="nsew")
        self.results_panel.columnconfigure(0, weight=1)

        # Vertical allocation: channel cards ~40%, benchmark ~25%, history ~35%
        self.results_panel.rowconfigure(0, weight=4)
        self.results_panel.rowconfigure(1, weight=3)
        self.results_panel.rowconfigure(2, weight=3)

        # Row 0: Dual Channel Cards
        self.cards_container = ttk.Frame(self.results_panel, style="TFrame")
        self.cards_container.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        self.cards_container.columnconfigure(0, weight=1)
        self.cards_container.columnconfigure(1, weight=1)
        self.cards_container.rowconfigure(0, weight=1)

        self.card_classical = ChannelCard(
            self.cards_container,
            title="CLASSICAL SOLVER CHANNEL",
        )
        self.card_classical.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.card_quantum = ChannelCard(
            self.cards_container,
            title="QUANTUM QAOA CHANNEL",
        )
        self.card_quantum.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # Aliases for canvas backward compatibility
        self.canvas_classical = self.card_classical.canvas
        self.canvas_quantum = self.card_quantum.canvas

        # Row 1: Benchmark Comparison Table
        self.benchmark_table = BenchmarkTable(self.results_panel)
        self.benchmark_table.grid(row=1, column=0, sticky="nsew", pady=(0, 12))

        # Row 2: Run History Table
        self.history_table = HistoryTable(self.results_panel)
        self.history_table.grid(row=2, column=0, sticky="nsew")

        # --------------------------------------------------------------------
        # Bottom Status Bar
        # --------------------------------------------------------------------
        self.status_bar = StatusBar(self)
        self.status_bar.pack(fill="x", side="bottom")

    # ========================================================================
    # TELEMETRY & LOGGING
    # ========================================================================
    def log(self, level: str, message: str) -> None:
        """Thread-safe telemetry and provenance logger."""
        self._dispatch_to_ui(self.setup_panel.log_panel.log, level, message)

    def _log(self, message: str) -> None:
        """Backward-compatible log handler routing through typed log."""
        msg_str = str(message)
        if "[FALLBACK" in msg_str or "fallback" in msg_str.lower():
            level = "WARN"
        elif "error" in msg_str.lower() or "exception" in msg_str.lower():
            level = "ERROR"
        elif "complete" in msg_str.lower() or "finished" in msg_str.lower():
            level = "OK"
        else:
            level = "INFO"
        self.log(level, msg_str)

    def _set_status(self, text: str, level: str = "normal") -> None:
        """Update status bar message."""
        self._dispatch_to_ui(self.status_bar.set_status, text, level)

    # ========================================================================
    # WORKSPACE & PRESET HANDLERS
    # ========================================================================
    def _on_preset_change(self, preset_name: str) -> None:
        """Switch active graph preset and reset visualizers."""
        self.current_graph = self.presets[preset_name]
        self.setup_panel.set_graph_info(
            self.current_graph.description,
            self.current_graph.node_count,
            self.current_graph.edge_count,
        )
        self.card_classical.reset(self.current_graph)
        self.card_quantum.reset(self.current_graph)
        self.benchmark_table.reset()
        self.log("INFO", f"Switched graph instance to: {preset_name}")

    def _reset_workspace(self) -> None:
        """Reset workspace to default preset and dual view."""
        self.workspace.reset_workspace()
        self.setup_panel.graph_var.set(self.workspace.active_graph.name)
        self.classical_result = None
        self.quantum_result = None
        self._on_preset_change(self.workspace.active_graph.name)
        self._apply_view_mode("dual")
        self.log("INFO", "Workspace reset to 4-Node Diamond and dual-channel layout.")

    def _randomise_graph(self) -> None:
        """Select a random predefined graph preset."""
        g = self.workspace.randomise_graph()
        self.setup_panel.graph_var.set(g.name)
        self.classical_result = None
        self.quantum_result = None
        self._on_preset_change(g.name)
        self.log("INFO", f"Randomised graph selection: {g.name}")

    def _toggle_view(self) -> None:
        """Toggle between dual, classical_only, and quantum_only views."""
        mode = self.workspace.toggle_view()
        self._apply_view_mode(mode)
        self.log("INFO", f"Switched workbench view mode to: [{mode}]")

    def _apply_view_mode(self, mode: str) -> None:
        """Adjust grid layout to show dual or single-channel views."""
        if mode == "dual":
            self.card_classical.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(0, 6))
            self.card_quantum.grid(row=0, column=1, columnspan=1, sticky="nsew", padx=(6, 0))
        elif mode == "classical_only":
            self.card_classical.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=0)
            self.card_quantum.grid_remove()
        elif mode == "quantum_only":
            self.card_quantum.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=0)
            self.card_classical.grid_remove()

    # ========================================================================
    # SOLVER EXECUTION: CLASSICAL
    # ========================================================================
    def _start_classical_thread(self) -> None:
        """Dispatch asynchronous classical solver thread."""
        threading.Thread(target=self._run_classical_logic, daemon=True).start()

    def _run_classical_logic(self, standalone: bool = True) -> None:
        """Execute deterministic or heuristic classical solver."""
        if standalone:
            self._dispatch_to_ui(self.setup_panel.set_busy, True)
            self._dispatch_to_ui(
                self.status_bar.start_job,
                "Solving Max-Cut classically...",
                30,
            )
        self._dispatch_to_ui(self.card_classical.set_running)
        self.log("INFO", f"Starting classical solver on {self.current_graph.name}...")

        try:
            if self.current_graph.node_count <= 16:
                exact_res = ClassicalSolver.solve_exact_brute_force(self.current_graph)
                self.classical_result = exact_res
            else:
                self.classical_result = ClassicalSolver.solve_greedy_local_search(self.current_graph)

            self.log(
                "OK",
                f"Classical solver finished: Cut {self.classical_result.cut_value}/"
                f"{self.classical_result.total_edges} in "
                f"{self.classical_result.execution_time_seconds * 1000.0:.2f}ms",
            )
            self._dispatch_to_ui(self._render_classical_results)

            # Record in history table
            self._dispatch_to_ui(
                self.history_table.add_entry,
                graph_name=self.current_graph.name,
                algorithm=f"Classical ({self.classical_result.algorithm_name})",
                p="—",
                shots="—",
                cut=self.classical_result.cut_value,
                ratio=self.classical_result.approximation_ratio,
                runtime_s=self.classical_result.execution_time_seconds,
                backend="CPU",
                status="Done",
            )

            if standalone:
                self._dispatch_to_ui(self.status_bar.stop_job, "Classical solution complete.", "done")
                self._dispatch_to_ui(self.setup_panel.set_busy, False)

        except Exception as exc:
            self.log("ERROR", f"Classical solver failed: {exc}")
            self._dispatch_to_ui(self.card_classical.set_error, str(exc))
            if standalone:
                self._dispatch_to_ui(self.status_bar.stop_job, f"Classical error: {exc}", "error")
                self._dispatch_to_ui(self.setup_panel.set_busy, False)

    def _render_classical_results(self) -> None:
        """Update classical channel card UI with results."""
        if not self.classical_result:
            return
        res = self.classical_result
        self.card_classical.update_results(
            graph=self.current_graph,
            status_text=f"Optimal ({res.algorithm_name})",
            set_s=res.set_s,
            set_not_s=res.set_not_s,
            cut_value=res.cut_value,
            total_edges=res.total_edges,
            best_bitstring=res.best_bitstring,
            badge_status="done",
            badge_text="DONE",
        )

    # ========================================================================
    # SOLVER EXECUTION: QUANTUM QAOA
    # ========================================================================
    def _start_quantum_thread(self) -> None:
        """Dispatch asynchronous quantum QAOA execution thread."""
        threading.Thread(target=self._run_quantum_logic, daemon=True).start()

    def _run_quantum_logic(self, standalone: bool = True) -> None:
        """Execute quantum QAOA with automated fallback recovery."""
        token = self.setup_panel.token_var.get().strip()
        depth = self.setup_panel.depth_var.get()
        shots = self.setup_panel.shots_var.get()
        timeout = float(self.setup_panel.timeout_var.get())

        if standalone:
            self._dispatch_to_ui(self.setup_panel.set_busy, True)
            self._dispatch_to_ui(
                self.status_bar.start_job,
                "Executing Quantum QAOA (monitoring IBM & Fallback)...",
                int(timeout),
            )
        self._dispatch_to_ui(self.card_quantum.set_running)
        self.log("INFO", f"Submitting QAOA job on {self.current_graph.name} (p={depth}, shots={shots})...")

        exact_cut = (
            self.classical_result.cut_value
            if self.classical_result and self.classical_result.algorithm_name == "Exact Brute-Force"
            else None
        )

        try:
            self.quantum_result = self.fallback_manager.execute_with_fallback(
                graph=self.current_graph,
                layer_depth=depth,
                shots=shots,
                token=token,
                exact_max_cut=exact_cut,
                log_callback=self._log,
                timeout_limit=timeout,
            )

            res = self.quantum_result
            if res.fallback_occurred:
                self.log("WARN", "IBM backend unavailable, using local fallback")
                badge_status = "fallback"
                badge_text = "FALLBACK"
                status_level = "fallback"
                status_msg = "IBM backend unavailable, using local fallback"
            else:
                self.log("OK", f"Quantum QAOA finished successfully on {res.backend_name}")
                badge_status = "done"
                badge_text = "DONE"
                status_level = "done"
                status_msg = "Quantum QAOA execution complete."

            self._dispatch_to_ui(self._render_quantum_results)

            # Record in history table
            runtime_to_record = (
                res.qpu_seconds if res.qpu_seconds is not None else res.execution_time_seconds
            )
            backend_label = res.backend_name
            if res.fallback_occurred:
                backend_label += " (Fallback)"

            self._dispatch_to_ui(
                self.history_table.add_entry,
                graph_name=self.current_graph.name,
                algorithm=f"QAOA (p={depth})",
                p=depth,
                shots=shots,
                cut=res.cut_value,
                ratio=res.approximation_ratio,
                runtime_s=runtime_to_record,
                backend=backend_label,
                status="Fallback" if res.fallback_occurred else "Done",
            )

            if standalone:
                self._dispatch_to_ui(self.status_bar.stop_job, status_msg, status_level)
                self._dispatch_to_ui(self.setup_panel.set_busy, False)

        except Exception as exc:
            self.log("ERROR", f"Quantum execution failed: {exc}")
            self._dispatch_to_ui(self.card_quantum.set_error, str(exc))
            if standalone:
                self._dispatch_to_ui(self.status_bar.stop_job, f"Quantum error: {exc}", "error")
                self._dispatch_to_ui(self.setup_panel.set_busy, False)

    def _render_quantum_results(self) -> None:
        """Update quantum channel card UI with results."""
        if not self.quantum_result:
            return
        res = self.quantum_result
        badge_status = "fallback" if res.fallback_occurred else "done"
        badge_text = "FALLBACK" if res.fallback_occurred else "DONE"
        status_label = f"[{res.provenance_label}] {'Fallback' if res.fallback_occurred else res.backend_name}"

        self.card_quantum.update_results(
            graph=self.current_graph,
            status_text=status_label,
            set_s=res.set_s,
            set_not_s=res.set_not_s,
            cut_value=res.cut_value,
            total_edges=res.total_edges,
            best_bitstring=res.best_bitstring,
            badge_status=badge_status,
            badge_text=badge_text,
        )

    # ========================================================================
    # SOLVER EXECUTION: BENCHMARK (SIDE-BY-SIDE)
    # ========================================================================
    def _start_benchmark_thread(self) -> None:
        """Dispatch asynchronous side-by-side comparative benchmark thread."""
        def run_both():
            timeout = int(self.setup_panel.timeout_var.get())
            self._dispatch_to_ui(self.setup_panel.set_busy, True)
            self._dispatch_to_ui(
                self.status_bar.start_job,
                "Running side-by-side benchmark comparison...",
                timeout + 30,
            )

            self._run_classical_logic(standalone=False)
            self._run_quantum_logic(standalone=False)

            self._dispatch_to_ui(self._update_comparative_summary)
            self._dispatch_to_ui(self.setup_panel.set_busy, False)
            self._dispatch_to_ui(
                self.status_bar.stop_job,
                "Done - Side-by-side benchmark comparison complete.",
                "done",
            )

        threading.Thread(target=run_both, daemon=True).start()

    def _update_comparative_summary(self) -> None:
        """Compute comparative benchmark metrics and update comparison table."""
        report = ComparativeAnalyticsEngine.compare(
            graph=self.current_graph,
            classical_result=self.classical_result,
            quantum_result=self.quantum_result,
            layer_depth=self.setup_panel.depth_var.get(),
            exact_max_cut=(
                self.classical_result.cut_value
                if self.classical_result and self.classical_result.algorithm_name == "Exact Brute-Force"
                else None
            ),
        )
        self.latest_report = report
        self.benchmark_table.update_from_report(
            report,
            self.classical_result,
            self.quantum_result,
        )

        if report.is_complete:
            self.log("INFO", "\n" + report.generate_ascii_summary())
        else:
            self.log("WARN", f"[Incomplete Benchmark] {report.placeholder_guidance}")
