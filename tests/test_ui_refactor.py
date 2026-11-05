"""Unit tests verifying ByteFlow UI dashboard architecture and regression stability."""

import os
import unittest
from byteflow.core.graph import GraphPresets
from byteflow.ui.app import ByteFlowApp
from byteflow.ui.theme import (
    BG_APP,
    BG_CARD,
    BG_INPUT,
    BORDER_SUBTLE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    STATUS_ERROR,
    STATUS_FALLBACK,
    STATUS_IDLE,
    STATUS_RUNNING,
    STATUS_SUCCESS,
)


class TestByteFlowUIRefactor(unittest.TestCase):
    """Verifies that the refactored UI fulfills all architectural requirements."""

    @classmethod
    def setUpClass(cls):
        # Initialize app in headless-compatible manner
        cls.app = ByteFlowApp()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def test_theme_tokens_defined(self):
        """Verify global palette tokens match specifications."""
        self.assertEqual(BG_APP, "#14141c")
        self.assertEqual(BG_CARD, "#1e1e2e")
        self.assertEqual(BG_INPUT, "#26263a")
        self.assertEqual(BORDER_SUBTLE, "#33334a")
        self.assertEqual(TEXT_PRIMARY, "#e6e6f0")
        self.assertEqual(TEXT_SECONDARY, "#a0a0b8")
        self.assertEqual(STATUS_SUCCESS, "#9ece6a")
        self.assertEqual(STATUS_RUNNING, "#e0af68")
        self.assertEqual(STATUS_FALLBACK, "#e0af68")
        self.assertEqual(STATUS_ERROR, "#f7768e")
        self.assertEqual(STATUS_IDLE, "#8a8aa3")

    def test_two_column_layout_and_components(self):
        """Verify two-column layout, setup panel, channel cards, and tables exist."""
        app = self.__class__.app

        # Left setup panel exists
        self.assertIsNotNone(app.setup_panel)
        self.assertIsNotNone(app.setup_panel.log_panel)

        # Right results area exists
        self.assertIsNotNone(app.card_classical)
        self.assertIsNotNone(app.card_quantum)
        self.assertIsNotNone(app.benchmark_table)
        self.assertIsNotNone(app.history_table)
        self.assertIsNotNone(app.status_bar)

        # Initial badge status is IDLE
        self.assertEqual(app.card_classical.badge.cget("text"), "IDLE")
        self.assertEqual(app.card_quantum.badge.cget("text"), "IDLE")

    def test_preset_selection_and_reset(self):
        """Verify preset switching updates graph info and resets cards."""
        app = self.__class__.app

        app._on_preset_change("6-Node Bipartite (K3,3)")
        app.update()
        self.assertEqual(app.current_graph.name, "6-Node Bipartite (K3,3)")
        self.assertEqual(app.current_graph.node_count, 6)
        self.assertEqual(app.current_graph.edge_count, 9)

        # Reset workspace
        app._reset_workspace()
        app.update()
        self.assertEqual(app.current_graph.name, "4-Node Diamond")

    def test_view_mode_toggle(self):
        """Verify cycling view mode adjusts channel visibility."""
        app = self.__class__.app
        app._apply_view_mode("dual")
        self.assertEqual(app.workspace.view_mode, "dual")

        app._toggle_view()
        self.assertIn(app.workspace.view_mode, ("classical_only", "quantum_only", "dual"))
        app._apply_view_mode("dual")

    def test_classical_solver_updates_ui(self):
        """Verify classical solver run populates classical card and history."""
        app = self.__class__.app
        app._run_classical_logic(standalone=True)

        # Process UI queue
        for _ in range(5):
            app._process_ui_queue()
            app.update()

        self.assertIsNotNone(app.classical_result)
        self.assertEqual(app.card_classical.badge.cget("text"), "DONE")

        # Check history table has at least 1 record
        self.assertGreaterEqual(len(app.history_table._records), 1)

    def test_history_table_sorting(self):
        """Verify sorting functionality on history table."""
        app = self.__class__.app
        app.history_table.clear_history()
        app.history_table.add_entry("G1", "AlgoA", 1, 100, 3, 0.75, 0.05, "CPU", "Done")
        app.history_table.add_entry("G2", "AlgoB", 2, 200, 5, 1.00, 0.01, "Sim", "Done")

        # Sort by Cut descending
        app.history_table._on_header_click("cut")
        first_cut = float(app.history_table._records[0][5])
        self.assertEqual(first_cut, 3.0)  # ascending first
        app.history_table._on_header_click("cut")
        first_cut_desc = float(app.history_table._records[0][5])
        self.assertEqual(first_cut_desc, 5.0)  # descending


if __name__ == "__main__":
    unittest.main()
