"""Channel card component for displaying solver execution state and partition metrics."""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from byteflow.core.graph import GraphInstance
from byteflow.ui.canvas import GraphVisualizerCanvas
from byteflow.ui.theme import (
    BG_CARD,
    BG_INPUT,
    BORDER_SUBTLE,
    FONT_FAMILY,
    FONT_MONO_SMALL,
    FONT_SECTION,
    FONT_SMALL_BOLD,
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_IDLE,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class StatusBadge(tk.Label):
    """Semantic status pill badge (Idle, Running, Done, Fallback, Error)."""

    def __init__(self, master, text: str = "Idle", status: str = "idle", **kwargs):
        super().__init__(
            master,
            text=text,
            font=FONT_SMALL_BOLD,
            bg=BG_INPUT,
            fg=STATUS_IDLE,
            padx=8,
            pady=2,
            relief="flat",
            **kwargs,
        )
        self.set_status(text, status)

    def set_status(self, text: str, status: str = "idle") -> None:
        color_map = {
            "idle": STATUS_IDLE,
            "running": STATUS_RUNNING,
            "done": STATUS_SUCCESS,
            "fallback": STATUS_FALLBACK,
            "error": STATUS_ERROR,
        }
        color = color_map.get(status.lower(), STATUS_IDLE)
        self.configure(text=text.upper(), fg=color)


class ChannelCard(ttk.Frame):
    """Card representing an individual execution channel (Classical or Quantum)."""

    PROPERTIES = [
        ("status", "Status"),
        ("part_a", "Partition A (S)"),
        ("part_b", "Partition B (V\\S)"),
        ("cut_edges", "Cut edges"),
        ("cut_value", "Cut value"),
        ("bitstring", "Best bitstring"),
    ]

    def __init__(self, master, title: str, **kwargs):
        super().__init__(master, style="Card.TFrame", padding=10, **kwargs)
        self._title_str = title
        self._current_graph: Optional[GraphInstance] = None

        # 1. Header Row
        header_row = ttk.Frame(self, style="Card.TFrame")
        header_row.pack(fill="x", pady=(0, 6))

        self.title_label = ttk.Label(
            header_row,
            text=title,
            style="CardHeader.TLabel",
        )
        self.title_label.pack(side="left")

        self.badge = StatusBadge(header_row, text="IDLE", status="idle")
        self.badge.pack(side="right")

        # 2. Graph Canvas (modest fixed ratio height)
        self.canvas = GraphVisualizerCanvas(self, height=135)
        self.canvas.pack(fill="x", pady=(0, 8))

        # 3. Key/Value Treeview
        tree_frame = ttk.Frame(self, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("Property", "Value"),
            show="headings",
            height=6,
            selectmode="none",
        )
        self.tree.heading("Property", text="Property", anchor="w")
        self.tree.heading("Value", text="Value", anchor="w")
        self.tree.column("Property", width=115, minwidth=90, stretch=False, anchor="w")
        self.tree.column("Value", width=180, minwidth=120, stretch=True, anchor="w")

        # Monospace styling tag for bitstring row
        self.tree.tag_configure("mono", font=FONT_MONO_SMALL)
        self.tree.tag_configure("normal", font=(FONT_FAMILY, 9))

        self.tree.pack(fill="both", expand=True)

        # Pre-populate rows with placeholders
        self._item_ids = {}
        for key, prop_name in self.PROPERTIES:
            tag = "mono" if key == "bitstring" else "normal"
            item_id = self.tree.insert("", "end", values=(prop_name, "—"), tags=(tag,))
            self._item_ids[key] = item_id

    def reset(self, graph: Optional[GraphInstance] = None) -> None:
        """Reset values to default placeholders and idle status."""
        self._current_graph = graph
        self.badge.set_status("IDLE", "idle")
        for key, prop_name in self.PROPERTIES:
            self.tree.item(self._item_ids[key], values=(prop_name, "—"))
        if graph:
            self.canvas.draw_graph(graph, None, f"{self._title_str} (Unsolved)")

    def set_running(self) -> None:
        """Set badge to running state."""
        self.badge.set_status("RUNNING", "running")
        self.tree.item(self._item_ids["status"], values=("Status", "Computing solution..."))

    def set_error(self, message: str = "Execution failed") -> None:
        """Set badge to error state."""
        self.badge.set_status("ERROR", "error")
        self.tree.item(self._item_ids["status"], values=("Status", message))

    def update_results(
        self,
        graph: GraphInstance,
        status_text: str,
        set_s: List[int],
        set_not_s: List[int],
        cut_value: int,
        total_edges: int,
        best_bitstring: str,
        badge_status: str = "done",
        badge_text: str = "DONE",
    ) -> None:
        """Populate the card with completed solver results."""
        self._current_graph = graph
        self.badge.set_status(badge_text, badge_status)

        # Redraw canvas
        self.canvas.draw_graph(
            graph,
            best_bitstring,
            f"{self._title_str} (Cut: {cut_value}/{total_edges})",
        )

        pct = (cut_value / total_edges * 100.0) if total_edges > 0 else 0.0
        cut_edges_str = f"{cut_value} / {total_edges} ({pct:.1f}%)"
        s_str = str(sorted(set_s)) if set_s else "[]"
        not_s_str = str(sorted(set_not_s)) if set_not_s else "[]"

        self.tree.item(self._item_ids["status"], values=("Status", status_text))
        self.tree.item(self._item_ids["part_a"], values=("Partition A (S)", s_str))
        self.tree.item(self._item_ids["part_b"], values=("Partition B (V\\S)", not_s_str))
        self.tree.item(self._item_ids["cut_edges"], values=("Cut edges", cut_edges_str))
        self.tree.item(self._item_ids["cut_value"], values=("Cut value", str(cut_value)))
        self.tree.item(self._item_ids["bitstring"], values=("Best bitstring", best_bitstring))
