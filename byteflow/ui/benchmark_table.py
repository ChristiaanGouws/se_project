"""Benchmark comparison table component (UC5 analytics)."""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from byteflow.analytics.comparative import ComparativeBenchmarkReport
from byteflow.solvers.classical import ClassicalResult
from byteflow.quantum.executor import QuantumExecutionResult
from byteflow.ui.theme import (
    BG_CARD,
    FONT_FAMILY,
    FONT_MONO_SMALL,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_IDLE,
    STATUS_SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class BenchmarkTable(ttk.Frame):
    """Table showing side-by-side metric comparison and deltas between Classical and Quantum."""

    ROWS = [
        ("cut", "Cut value"),
        ("ratio", "Approximation ratio"),
        ("runtime", "Runtime (s)"),
        ("backend", "Backend"),
        ("params", "Shots / depth p"),
        ("bitstring", "Best bitstring"),
        ("verdict", "Result"),
    ]

    def __init__(self, master, **kwargs):
        super().__init__(master, style="Card.TFrame", padding=10, **kwargs)

        # Header Frame
        hdr_frame = ttk.Frame(self, style="Card.TFrame")
        hdr_frame.pack(fill="x", pady=(0, 4))

        title = ttk.Label(
            hdr_frame,
            text="BENCHMARK COMPARISON & PROVENANCE",
            style="CardHeader.TLabel",
        )
        title.pack(side="left")

        # Empty state guidance hint
        self.hint_label = ttk.Label(
            hdr_frame,
            text="Select an experiment graph and trigger the benchmark to compare algorithms.",
            style="Secondary.TLabel",
        )
        self.hint_label.pack(side="right")

        # Treeview
        columns = ("Metric", "Classical", "Quantum QAOA", "Delta")
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=7,
            selectmode="none",
        )

        col_widths = {
            "Metric": (140, 120, False, "w"),
            "Classical": (160, 130, True, "center"),
            "Quantum QAOA": (180, 140, True, "center"),
            "Delta": (120, 100, False, "center"),
        }

        for col, (w, mw, stretch, align) in col_widths.items():
            self.tree.heading(col, text=col, anchor=align)
            self.tree.column(col, width=w, minwidth=mw, stretch=stretch, anchor=align)

        # Tags for status and typography
        self.tree.tag_configure("tag_green", foreground=STATUS_SUCCESS)
        self.tree.tag_configure("tag_amber", foreground=STATUS_FALLBACK)
        self.tree.tag_configure("tag_red", foreground=STATUS_ERROR)
        self.tree.tag_configure("tag_mono", font=FONT_MONO_SMALL)
        self.tree.tag_configure("tag_default", foreground=TEXT_PRIMARY)

        self.tree.pack(fill="both", expand=True)

        self._row_ids = {}
        self.reset()

    def reset(self) -> None:
        """Reset table to initial placeholder state."""
        self.hint_label.configure(
            text="Select an experiment graph and trigger the benchmark to compare algorithms."
        )
        self.tree.delete(*self.tree.get_children())
        self._row_ids.clear()

        for key, name in self.ROWS:
            tag = "tag_mono" if key == "bitstring" else "tag_default"
            item_id = self.tree.insert("", "end", values=(name, "—", "—", "—"), tags=(tag,))
            self._row_ids[key] = item_id

    def update_from_report(
        self,
        report: ComparativeBenchmarkReport,
        classical_res: Optional[ClassicalResult] = None,
        quantum_res: Optional[QuantumExecutionResult] = None,
    ) -> None:
        """Populate the comparison table with benchmark data."""
        if not report.is_complete:
            self.hint_label.configure(
                text=report.placeholder_guidance or "Incomplete benchmark state."
            )
            return

        self.hint_label.configure(text="")

        c_cut = report.classical_cut
        q_cut = report.quantum_cut
        delta_cut = report.cut_difference
        delta_cut_str = f"{delta_cut:+d}" if delta_cut is not None else "—"

        # 1. Cut value
        cut_tag = (
            "tag_green"
            if delta_cut is not None and delta_cut >= 0
            else "tag_amber"
            if delta_cut is not None and delta_cut == -1
            else "tag_red"
        )
        self.tree.item(
            self._row_ids["cut"],
            values=(
                "Cut value",
                f"{c_cut} / {report.edge_count}",
                f"{q_cut} / {report.edge_count}",
                delta_cut_str,
            ),
            tags=(cut_tag,),
        )

        # 2. Approximation ratio
        c_ratio = report.classical_approximation_ratio
        q_ratio = report.quantum_approximation_ratio
        delta_ratio_str = "—"
        ratio_tag = "tag_default"
        if c_ratio is not None and q_ratio is not None:
            delta_ratio = q_ratio - c_ratio
            delta_ratio_str = f"{delta_ratio:+.3f}"
            ratio_tag = (
                "tag_green"
                if delta_ratio >= 0
                else "tag_amber"
                if delta_ratio >= -0.15
                else "tag_red"
            )

        c_ratio_str = f"{c_ratio:.3f}" if c_ratio is not None else "—"
        q_ratio_str = f"{q_ratio:.3f}" if q_ratio is not None else "—"
        self.tree.item(
            self._row_ids["ratio"],
            values=("Approximation ratio", c_ratio_str, q_ratio_str, delta_ratio_str),
            tags=(ratio_tag,),
        )

        # 3. Runtime
        c_rt = report.classical_runtime_seconds or 0.0
        q_rt = (
            report.quantum_qpu_seconds
            if report.quantum_qpu_seconds is not None
            else (report.quantum_runtime_seconds or 0.0)
        )
        delta_rt = q_rt - c_rt
        self.tree.item(
            self._row_ids["runtime"],
            values=(
                "Runtime (s)",
                f"{c_rt:.4f}s",
                f"{q_rt:.4f}s",
                f"{delta_rt:+.4f}s",
            ),
            tags=("tag_default",),
        )

        # 4. Backend
        c_backend = report.classical_algorithm or "CPU"
        q_backend = report.quantum_backend or "Local Sim"
        if report.quantum_fallback_occurred:
            q_backend += " (Fallback)"
        self.tree.item(
            self._row_ids["backend"],
            values=("Backend", c_backend, q_backend, "—"),
            tags=("tag_amber" if report.quantum_fallback_occurred else "tag_default",),
        )

        # 5. Parameters
        q_params = f"{report.quantum_shots or '—'} shots / p={report.quantum_layer_depth or 1}"
        self.tree.item(
            self._row_ids["params"],
            values=("Shots / depth p", "N/A", q_params, "—"),
            tags=("tag_default",),
        )

        # 6. Bitstring
        c_bits = classical_res.best_bitstring if classical_res else "—"
        q_bits = quantum_res.best_bitstring if quantum_res else "—"
        self.tree.item(
            self._row_ids["bitstring"],
            values=("Best bitstring", c_bits, q_bits, "—"),
            tags=("tag_mono",),
        )

        # 7. Verdict
        if report.quantum_exceeded_classical:
            verdict_text = "Quantum Surpassed"
            verdict_tag = "tag_green"
        elif report.quantum_matched_classical:
            verdict_text = "Quantum Matched"
            verdict_tag = "tag_green"
        elif delta_cut == -1:
            verdict_text = "Near Optimal (-1)"
            verdict_tag = "tag_amber"
        else:
            verdict_text = f"Classical Outperformed ({delta_cut:+d})"
            verdict_tag = "tag_red"

        self.tree.item(
            self._row_ids["verdict"],
            values=("Result", "Baseline", verdict_text, "—"),
            tags=(verdict_tag,),
        )
