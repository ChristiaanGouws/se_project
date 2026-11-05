"""Run history table component with sorting, zebra striping, and CSV export."""

import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, List, Optional

from byteflow.ui.theme import (
    BG_CARD,
    BG_INPUT,
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


class HistoryTable(ttk.Frame):
    """Historical execution table tracking all runs with sorting and CSV export."""

    COLUMNS = (
        ("time", "Time", 75, "center", False),
        ("graph", "Graph", 120, "w", True),
        ("algo", "Algorithm", 95, "w", False),
        ("p", "p", 40, "center", False),
        ("shots", "Shots", 60, "e", False),
        ("cut", "Cut", 55, "e", False),
        ("ratio", "Ratio", 55, "e", False),
        ("runtime", "Runtime (s)", 80, "e", False),
        ("backend", "Backend", 110, "w", True),
        ("status", "Status", 75, "center", False),
    )

    NUMERIC_COLS = {"p", "shots", "cut", "ratio", "runtime"}

    def __init__(self, master, **kwargs):
        super().__init__(master, style="Card.TFrame", padding=10, **kwargs)
        self._sort_col: Optional[str] = None
        self._sort_reverse: bool = False
        self._records: List[List[str]] = []

        # 1. Header Toolbar
        hdr_frame = ttk.Frame(self, style="Card.TFrame")
        hdr_frame.pack(fill="x", pady=(0, 6))

        title = ttk.Label(
            hdr_frame,
            text="RUN HISTORY & BENCHMARK AUDIT",
            style="CardHeader.TLabel",
        )
        title.pack(side="left")

        btn_box = ttk.Frame(hdr_frame, style="Card.TFrame")
        btn_box.pack(side="right")

        self.btn_export = ttk.Button(
            btn_box,
            text="Export CSV",
            style="Small.TButton",
            command=self.export_csv,
        )
        self.btn_export.pack(side="left", padx=(0, 4))

        self.btn_clear = ttk.Button(
            btn_box,
            text="Clear History",
            style="Small.TButton",
            command=self.clear_history,
        )
        self.btn_clear.pack(side="left")

        # 2. Treeview with Scrollbar
        tbl_frame = ttk.Frame(self, style="Card.TFrame")
        tbl_frame.pack(fill="both", expand=True)

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(
            tbl_frame,
            columns=col_ids,
            show="headings",
            height=6,
            selectmode="browse",
        )

        scrollbar = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        for col_id, col_name, width, align, stretch in self.COLUMNS:
            self.tree.heading(
                col_id,
                text=col_name,
                anchor=align,
                command=lambda c=col_id: self._on_header_click(c),
            )
            self.tree.column(
                col_id,
                width=width,
                minwidth=35,
                stretch=stretch,
                anchor=align,
            )

        # Tags configuration
        self.tree.tag_configure("odd_row", background="#1e1e2e")
        self.tree.tag_configure("even_row", background="#232336")
        self.tree.tag_configure("status_done", foreground=STATUS_SUCCESS)
        self.tree.tag_configure("status_fallback", foreground=STATUS_FALLBACK)
        self.tree.tag_configure("status_error", foreground=STATUS_ERROR)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def add_entry(
        self,
        graph_name: str,
        algorithm: str,
        p: Any,
        shots: Any,
        cut: Any,
        ratio: Any,
        runtime_s: Any,
        backend: str,
        status: str,
    ) -> None:
        """Append a completed execution record to the history table."""
        now_str = datetime.now().strftime("%H:%M:%S")

        p_str = str(p) if p is not None else "—"
        shots_str = str(shots) if shots is not None else "—"
        cut_str = str(cut) if cut is not None else "—"
        ratio_str = f"{float(ratio):.3f}" if ratio is not None else "—"
        if isinstance(runtime_s, (int, float)):
            rt_str = f"{float(runtime_s):.4f}"
        else:
            rt_str = str(runtime_s) if runtime_s is not None else "—"

        row = [
            now_str,
            str(graph_name),
            str(algorithm),
            p_str,
            shots_str,
            cut_str,
            ratio_str,
            rt_str,
            str(backend),
            str(status),
        ]
        self._records.append(row)
        self._render_records()

    def _render_records(self) -> None:
        """Re-populate treeview rows with alternating zebra striping."""
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self._records):
            stripe_tag = "even_row" if idx % 2 == 0 else "odd_row"
            status_val = row[9].lower()
            if "fallback" in status_val:
                status_tag = "status_fallback"
            elif "err" in status_val or "fail" in status_val:
                status_tag = "status_error"
            else:
                status_tag = "status_done"

            self.tree.insert("", "end", values=row, tags=(stripe_tag, status_tag))

    def _on_header_click(self, col_id: str) -> None:
        """Sort rows numerically or alphabetically upon column header click."""
        if self._sort_col == col_id:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col_id
            self._sort_reverse = False

        col_idx = [c[0] for c in self.COLUMNS].index(col_id)
        is_numeric = col_id in self.NUMERIC_COLS

        def parse_key(row):
            val = row[col_idx]
            if is_numeric:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return float("-inf")
            return val.lower()

        self._records.sort(key=parse_key, reverse=self._sort_reverse)

        # Update headers with sorting indicator arrows
        arrow = " ▼" if self._sort_reverse else " ▲"
        for c_id, c_name, _, align, _ in self.COLUMNS:
            display_name = f"{c_name}{arrow}" if c_id == col_id else c_name
            self.tree.heading(c_id, text=display_name, anchor=align)

        self._render_records()

    def clear_history(self) -> None:
        """Clear all historical run records."""
        self._records.clear()
        self.tree.delete(*self.tree.get_children())

    def export_csv(self) -> None:
        """Prompt user with file save dialog and export rows to CSV."""
        if not self._records:
            messagebox.showinfo("Export CSV", "No history records to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Benchmark History",
            initialfile=f"byteflow_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = [c[1] for c in self.COLUMNS]
                writer.writerow(headers)
                writer.writerows(self._records)
            messagebox.showinfo("Export Successful", f"Saved {len(self._records)} rows to:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not write CSV file:\n{exc}")
