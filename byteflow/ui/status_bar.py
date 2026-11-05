"""Status bar component with semantic alerts, indeterminate progress, and live timer."""

import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from byteflow.ui.theme import (
    BG_APP,
    BG_INPUT,
    FONT_FAMILY,
    FONT_MONO_SMALL,
    FONT_SMALL,
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_IDLE,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class StatusBar(ttk.Frame):
    """Bottom status bar with real-time job feedback, progressbar, and elapsed clock."""

    def __init__(self, master, **kwargs):
        super().__init__(master, padding=(16, 6, 16, 8), **kwargs)

        # 1. Status Message (Left)
        self.status_label = tk.Label(
            self,
            text="Ready. Virtual Laboratory online.",
            font=FONT_SMALL,
            bg=BG_APP,
            fg=TEXT_SECONDARY,
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        # 2. Indeterminate Progressbar (Center)
        self.progress = ttk.Progressbar(
            self,
            mode="indeterminate",
            length=160,
            style="Horizontal.TProgressbar",
        )
        # Initially hidden

        # 3. Live Elapsed Timer (Right)
        self.timer_label = tk.Label(
            self,
            text="Elapsed: --:--",
            font=FONT_MONO_SMALL,
            bg=BG_APP,
            fg=TEXT_MUTED,
            anchor="e",
        )
        self.timer_label.pack(side="right", padx=(8, 0))

        self._timer_running: bool = False
        self._start_time: float = 0.0
        self._timeout_seconds: int = 180
        self._timer_id: Optional[str] = None

    def set_status(self, text: str, level: str = "normal") -> None:
        """Update status text and semantic text color."""
        color_map = {
            "normal": TEXT_SECONDARY,
            "running": STATUS_RUNNING,
            "fallback": STATUS_FALLBACK,
            "success": STATUS_SUCCESS,
            "done": STATUS_SUCCESS,
            "error": STATUS_ERROR,
        }
        color = color_map.get(level.lower(), TEXT_SECONDARY)
        self.status_label.configure(text=text, fg=color)

    def start_job(self, status_msg: str, timeout_seconds: int = 180) -> None:
        """Show progressbar, start timer, and display running status."""
        self.set_status(status_msg, level="running")
        self.progress.pack(side="right", padx=(8, 8))
        self.progress.start(12)

        self._timeout_seconds = timeout_seconds
        self._start_time = time.time()
        self._timer_running = True
        self.timer_label.configure(fg=TEXT_PRIMARY)
        self._tick_timer()

    def stop_job(self, status_msg: str, level: str = "success") -> None:
        """Stop progressbar, finalize timer, and display completion/error state."""
        self.set_status(status_msg, level=level)
        self.progress.stop()
        self.progress.pack_forget()

        self._timer_running = False
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None

        if self._start_time > 0:
            elapsed = int(time.time() - self._start_time)
            m, s = divmod(elapsed, 60)
            self.timer_label.configure(
                text=f"Last run: {m:02d}:{s:02d}",
                fg=TEXT_MUTED,
            )

    def _tick_timer(self) -> None:
        """Update elapsed timer display every 500ms."""
        if not self._timer_running:
            return

        elapsed = int(time.time() - self._start_time)
        e_m, e_s = divmod(elapsed, 60)
        t_m, t_s = divmod(self._timeout_seconds, 60)
        self.timer_label.configure(
            text=f"Elapsed: {e_m:02d}:{e_s:02d} / timeout {t_m:02d}:{t_s:02d}"
        )
        self._timer_id = self.after(500, self._tick_timer)
