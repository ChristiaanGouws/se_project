"""Visualizer canvas component for rendering graph topologies and partition cuts."""

import math
import tkinter as tk
from typing import Dict, Optional, Tuple

from byteflow.core.graph import GraphInstance
from byteflow.ui.theme import (
    BG_CARD,
    EDGE_CUT,
    EDGE_UNCUT,
    FONT_FAMILY,
    NODE_SET_0,
    NODE_SET_1,
    NODE_UNPARTITIONED,
    TEXT_DARK,
    TEXT_SECONDARY,
)


class GraphVisualizerCanvas(tk.Canvas):
    """Draws graph topologies and highlights partition cuts in a compact canvas."""

    def __init__(self, master, height: int = 150, **kwargs):
        super().__init__(
            master,
            bg=BG_CARD,
            height=height,
            highlightthickness=0,
            **kwargs,
        )
        self.node_radius = 13
        self._last_graph: Optional[GraphInstance] = None
        self._last_partition: Optional[str] = None
        self._last_title: Optional[str] = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event) -> None:
        if self._last_graph is not None:
            self.draw_graph(self._last_graph, self._last_partition, self._last_title or "")

    def draw_graph(
        self,
        graph: GraphInstance,
        partition_bitstring: Optional[str] = None,
        title: str = "",
    ) -> None:
        """Render the graph vertices and edges with partition coloring."""
        self._last_graph = graph
        self._last_partition = partition_bitstring
        self._last_title = title

        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10:
            w = 300
        if h < 10:
            h = 150

        # Optional subtle subtitle / tag in top-left
        if title:
            self.create_text(
                10,
                12,
                text=title,
                anchor="w",
                fill=TEXT_SECONDARY,
                font=(FONT_FAMILY, 8),
            )

        n = graph.node_count
        if n == 0:
            return

        center_x = w / 2.0
        center_y = (h / 2.0) + (6 if title else 0)
        radius = min(w / 2.0 - 24, h / 2.0 - 18)
        if radius < 20:
            radius = 20

        coords: Dict[int, Tuple[float, float]] = {}

        # Circular layout
        for i in range(n):
            angle = (2.0 * math.pi * i / n) - (math.pi / 2.0)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            coords[i] = (x, y)

        # Draw edges
        for u, v in graph.edges:
            x1, y1 = coords[u]
            x2, y2 = coords[v]

            is_cut = (
                partition_bitstring is not None
                and len(partition_bitstring) == n
                and partition_bitstring[u] != partition_bitstring[v]
            )

            if is_cut:
                self.create_line(x1, y1, x2, y2, fill=EDGE_CUT, width=2.5)
            else:
                dash = (3, 3) if partition_bitstring else ()
                self.create_line(x1, y1, x2, y2, fill=EDGE_UNCUT, width=1.2, dash=dash)

        # Draw vertices
        r = self.node_radius
        for i in range(n):
            x, y = coords[i]

            if partition_bitstring and len(partition_bitstring) == n:
                fill_color = NODE_SET_0 if partition_bitstring[i] == "0" else NODE_SET_1
            else:
                fill_color = NODE_UNPARTITIONED

            # Node circle
            self.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=fill_color,
                outline=BG_CARD,
                width=1.5,
            )
            # Node label
            self.create_text(
                x,
                y,
                text=str(i),
                fill=TEXT_DARK,
                font=(FONT_FAMILY, 8, "bold"),
            )
