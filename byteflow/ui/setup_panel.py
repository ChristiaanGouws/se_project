"""Setup and configuration panel for graph selection, QAOA hyperparameters, and solver dispatch."""

import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

from byteflow.ui.log_panel import LogPanel
from byteflow.ui.theme import (
    BG_CARD,
    BORDER_SUBTLE,
    FONT_FAMILY,
    FONT_SECTION,
    FONT_SMALL,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class SetupPanel(ttk.Frame):
    """Left column containing grouped setup cards, execution actions, and telemetry."""

    def __init__(
        self,
        master,
        preset_names: List[str],
        on_preset_change: Callable[[str], None],
        on_reset: Callable[[], None],
        on_randomise: Callable[[], None],
        on_toggle_view: Callable[[], None],
        on_run_classical: Callable[[], None],
        on_run_quantum: Callable[[], None],
        on_run_benchmark: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, style="TFrame", **kwargs)

        self._on_preset_change_cb = on_preset_change
        self._on_reset_cb = on_reset
        self._on_randomise_cb = on_randomise
        self._on_toggle_view_cb = on_toggle_view
        self._on_run_classical_cb = on_run_classical
        self._on_run_quantum_cb = on_run_quantum
        self._on_run_benchmark_cb = on_run_benchmark

        # State variables
        self.graph_var = tk.StringVar(value=preset_names[0] if preset_names else "")
        self.depth_var = tk.IntVar(value=1)
        self.shots_var = tk.IntVar(value=1024)
        self.timeout_var = tk.IntVar(value=180)
        self.token_var = tk.StringVar(value=os.getenv("QISKIT_IBM_TOKEN", ""))
        self.show_token_var = tk.BooleanVar(value=False)

        self._build_widgets(preset_names)

    def _build_widgets(self, preset_names: List[str]) -> None:
        # ====================================================================
        # 1. Graph Section Card
        # ====================================================================
        sec_graph = ttk.LabelFrame(self, text="Graph Selection", padding=(12, 8, 12, 10))
        sec_graph.pack(fill="x", pady=(0, 10))

        self.graph_dropdown = ttk.Combobox(
            sec_graph,
            textvariable=self.graph_var,
            values=preset_names,
            state="readonly",
        )
        self.graph_dropdown.pack(fill="x", pady=(2, 6))
        self.graph_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda _e: self._on_preset_change_cb(self.graph_var.get()),
        )

        # Action buttons row: Reset, Random, View Mode
        btn_row = ttk.Frame(sec_graph, style="Card.TFrame")
        btn_row.pack(fill="x", pady=(0, 6))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)

        self.btn_reset = ttk.Button(
            btn_row,
            text="Reset",
            style="Secondary.TButton",
            command=self._on_reset_cb,
        )
        self.btn_reset.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.btn_random = ttk.Button(
            btn_row,
            text="Random",
            style="Secondary.TButton",
            command=self._on_randomise_cb,
        )
        self.btn_random.grid(row=0, column=1, sticky="ew", padx=3)

        self.btn_view_mode = ttk.Button(
            btn_row,
            text="View Mode",
            style="Secondary.TButton",
            command=self._on_toggle_view_cb,
        )
        self.btn_view_mode.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        # Description label
        self.graph_desc_label = ttk.Label(
            sec_graph,
            text="",
            style="Secondary.TLabel",
            wraplength=290,
            justify="left",
        )
        self.graph_desc_label.pack(fill="x", pady=(2, 0))

        # ====================================================================
        # 2. QAOA Hyperparameters Section Card
        # ====================================================================
        sec_params = ttk.LabelFrame(self, text="QAOA Parameters", padding=(12, 8, 12, 10))
        sec_params.pack(fill="x", pady=(0, 10))
        sec_params.columnconfigure(0, weight=1)
        sec_params.columnconfigure(1, weight=0)

        # Depth (p)
        lbl_depth = ttk.Label(sec_params, text="Layer depth (p):", style="Card.TLabel")
        lbl_depth.grid(row=0, column=0, sticky="w", pady=3)
        self.spin_depth = ttk.Spinbox(
            sec_params,
            from_=1,
            to=10,
            textvariable=self.depth_var,
            width=9,
        )
        self.spin_depth.grid(row=0, column=1, sticky="e", pady=3)

        # Shots
        lbl_shots = ttk.Label(sec_params, text="Measurement shots:", style="Card.TLabel")
        lbl_shots.grid(row=1, column=0, sticky="w", pady=3)
        self.spin_shots = ttk.Spinbox(
            sec_params,
            values=[128, 256, 512, 1024, 2048, 4096],
            textvariable=self.shots_var,
            width=9,
        )
        self.spin_shots.grid(row=1, column=1, sticky="e", pady=3)

        # Timeout
        lbl_timeout = ttk.Label(sec_params, text="IBM timeout (s):", style="Card.TLabel")
        lbl_timeout.grid(row=2, column=0, sticky="w", pady=3)
        self.spin_timeout = ttk.Spinbox(
            sec_params,
            values=[30, 60, 120, 180, 300, 600],
            textvariable=self.timeout_var,
            width=9,
        )
        self.spin_timeout.grid(row=2, column=1, sticky="e", pady=3)

        # ====================================================================
        # 3. IBM Quantum Connection Section Card
        # ====================================================================
        sec_ibm = ttk.LabelFrame(self, text="IBM Connection", padding=(12, 8, 12, 10))
        sec_ibm.pack(fill="x", pady=(0, 10))

        token_row = ttk.Frame(sec_ibm, style="Card.TFrame")
        token_row.pack(fill="x", pady=(2, 4))

        self.token_entry = ttk.Entry(
            token_row,
            textvariable=self.token_var,
            show="•",
        )
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.chk_show_token = ttk.Checkbutton(
            token_row,
            text="Show",
            variable=self.show_token_var,
            command=self._on_toggle_token_visibility,
        )
        self.chk_show_token.pack(side="right")

        lbl_token_help = ttk.Label(
            sec_ibm,
            text="Leave blank to use local fallback simulation",
            style="Secondary.TLabel",
        )
        lbl_token_help.pack(anchor="w", pady=(2, 0))

        # ====================================================================
        # 4. Actions Section Card
        # ====================================================================
        sec_actions = ttk.LabelFrame(self, text="Actions", padding=(12, 8, 12, 10))
        sec_actions.pack(fill="x", pady=(0, 10))

        self.btn_benchmark = ttk.Button(
            sec_actions,
            text="Run Side-by-Side Benchmark",
            style="Primary.TButton",
            command=self._on_run_benchmark_cb,
        )
        self.btn_benchmark.pack(fill="x", pady=(2, 6))

        self.btn_classical = ttk.Button(
            sec_actions,
            text="Run Classical Baseline",
            style="Secondary.TButton",
            command=self._on_run_classical_cb,
        )
        self.btn_classical.pack(fill="x", pady=(0, 6))

        self.btn_quantum = ttk.Button(
            sec_actions,
            text="Run Quantum QAOA (with Fallback)",
            style="Secondary.TButton",
            command=self._on_run_quantum_cb,
        )
        self.btn_quantum.pack(fill="x", pady=(0, 2))

        # ====================================================================
        # 5. Telemetry & Provenance Log (Embedded at bottom)
        # ====================================================================
        self.log_panel = LogPanel(self)
        self.log_panel.pack(fill="both", expand=True)

    def _on_toggle_token_visibility(self) -> None:
        """Toggle token masking between bullets and cleartext."""
        if self.show_token_var.get():
            self.token_entry.configure(show="")
        else:
            self.token_entry.configure(show="•")

    def set_graph_info(self, description: str, node_count: int, edge_count: int) -> None:
        """Update graph description and vertex/edge counts."""
        info = f"{description}\nVertices: {node_count}  |  Edges: {edge_count}"
        self.graph_desc_label.configure(text=info)

    def set_busy(self, is_busy: bool) -> None:
        """Toggle action buttons between active and disabled states during execution."""
        state = "disabled" if is_busy else "normal"
        self.btn_benchmark.configure(state=state)
        self.btn_classical.configure(state=state)
        self.btn_quantum.configure(state=state)
        self.btn_reset.configure(state=state)
        self.btn_random.configure(state=state)
