"""Telemetry and provenance logging panel with semantic tag styling and text export."""

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Optional

from byteflow.ui.theme import (
    BG_CARD,
    BG_INPUT,
    FONT_MONO_LOG,
    FONT_SECTION,
    FONT_SMALL,
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_IDLE,
    STATUS_SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class LogPanel(ttk.Frame):
    """Telemetry log widget with syntax highlighting, auto-scroll, and export."""

    def __init__(self, master, **kwargs):
        super().__init__(master, style="Card.TFrame", padding=8, **kwargs)

        # Header toolbar
        hdr = ttk.Frame(self, style="Card.TFrame")
        hdr.pack(fill="x", pady=(0, 4))

        title = ttk.Label(
            hdr,
            text="TELEMETRY & LOG",
            style="CardHeader.TLabel",
        )
        title.pack(side="left")

        btn_box = ttk.Frame(hdr, style="Card.TFrame")
        btn_box.pack(side="right")

        self.btn_export = ttk.Button(
            btn_box,
            text="Export .txt",
            style="Small.TButton",
            command=self.export_txt,
        )
        self.btn_export.pack(side="left", padx=(0, 4))

        self.btn_clear = ttk.Button(
            btn_box,
            text="Clear",
            style="Small.TButton",
            command=self.clear,
        )
        self.btn_clear.pack(side="left")

        # Read-only ScrolledText
        self.text_area = ScrolledText(
            self,
            bg=BG_INPUT,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            font=FONT_MONO_LOG,
            wrap="word",
            height=7,
            borderwidth=0,
            highlightthickness=0,
        )
        self.text_area.pack(fill="both", expand=True)

        # Configure semantic coloring tags
        self.text_area.tag_configure("tag_time", foreground=TEXT_MUTED)
        self.text_area.tag_configure("tag_INFO", foreground=TEXT_SECONDARY)
        self.text_area.tag_configure("tag_WARN", foreground=STATUS_FALLBACK)
        self.text_area.tag_configure("tag_ERROR", foreground=STATUS_ERROR)
        self.text_area.tag_configure("tag_OK", foreground=STATUS_SUCCESS)
        self.text_area.tag_configure("tag_msg", foreground=TEXT_PRIMARY)

        self.text_area.configure(state="disabled")

    def log(self, level: str, message: str) -> None:
        """Append a formatted line: HH:MM:SS  LEVEL  message with semantic coloring."""
        lvl_norm = level.upper().strip()
        if lvl_norm not in ("INFO", "WARN", "ERROR", "OK"):
            lvl_norm = "INFO"

        now_str = datetime.now().strftime("%H:%M:%S")

        self.text_area.configure(state="normal")
        self.text_area.insert("end", f"{now_str}  ", "tag_time")
        self.text_area.insert("end", f"{lvl_norm:<5}  ", f"tag_{lvl_norm}")
        self.text_area.insert("end", f"{message}\n", "tag_msg")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def clear(self) -> None:
        """Clear telemetry log entries."""
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.configure(state="disabled")

    def export_txt(self) -> None:
        """Export log contents to a text file."""
        content = self.text_area.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Export Log", "Telemetry log is currently empty.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Telemetry Log",
            initialfile=f"byteflow_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Export Successful", f"Saved telemetry log to:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not write log file:\n{exc}")
