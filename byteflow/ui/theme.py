"""ByteFlow UI Design System & Theme Engine.

Centralizes color palettes, typography scales, spacing tokens, and ttk styles
for the dark dashboard interface. Adheres to WCAG AA contrast standards.
"""

import tkinter as tk
from tkinter import ttk

# ============================================================================
# 1. COLOR PALETTE
# ============================================================================
BG_APP = "#14141c"            # Deep workspace background
BG_CARD = "#1e1e2e"           # Card and panel container background
BG_INPUT = "#26263a"          # Raised / input / field background
BORDER_SUBTLE = "#33334a"     # 1px border for panels and dividers
BORDER_FOCUS = "#7aa2f7"      # Accent border on focus

# Text tokens
TEXT_PRIMARY = "#e6e6f0"      # High-contrast primary text
TEXT_SECONDARY = "#a0a0b8"    # Clearly readable secondary text (WCAG AA > 6:1 on #1e1e2e)
TEXT_MUTED = "#6c7086"        # Disabled / subtle label text
TEXT_DARK = "#14141c"         # Dark text on bright accent buttons

# Accent tokens
ACCENT = "#7aa2f7"            # Primary brand accent (soft electric blue)
ACCENT_HOVER = "#89b4fa"      # Accent hover state
ACCENT_PRESSED = "#6588d6"    # Accent active/pressed state

# Semantic Status Colors
STATUS_SUCCESS = "#9ece6a"    # Green (Done / optimal match)
STATUS_RUNNING = "#e0af68"    # Amber (Job in progress)
STATUS_FALLBACK = "#e0af68"   # Amber (Local simulation fallback)
STATUS_ERROR = "#f7768e"      # Red (Failure / error)
STATUS_IDLE = "#8a8aa3"       # Neutral grey (Awaiting execution)

# Visualizer Specific Colors
NODE_SET_0 = "#7aa2f7"        # Partition S (Accent blue)
NODE_SET_1 = "#9ece6a"        # Partition V \ S (Success green)
NODE_UNPARTITIONED = "#8a8aa3"
EDGE_CUT = "#f7768e"          # Cut edge highlight (Red-pink)
EDGE_UNCUT = "#33334a"        # Uncut edge muted

# ============================================================================
# 2. TYPOGRAPHY SCALE
# ============================================================================
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 10)
FONT_BODY = (FONT_FAMILY, 10)
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")

FONT_MONO_BODY = (FONT_MONO, 10)
FONT_MONO_SMALL = (FONT_MONO, 9)
FONT_MONO_LOG = (FONT_MONO, 9)

# ============================================================================
# 3. SPACING GRID (8px Scale)
# ============================================================================
PAD_XS = 4
PAD_SM = 8
PAD_MD = 16
PAD_LG = 24


def apply_theme(root: tk.Tk) -> ttk.Style:
    """Configures the dark ttk style using 'clam' as the foundation."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG_APP)

    # Base Frame styles
    style.configure("TFrame", background=BG_APP)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Input.TFrame", background=BG_INPUT)

    # Base Labels
    style.configure(
        "TLabel",
        background=BG_APP,
        foreground=TEXT_PRIMARY,
        font=FONT_BODY,
    )
    style.configure(
        "Card.TLabel",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        font=FONT_BODY,
    )
    style.configure(
        "Header.TLabel",
        background=BG_APP,
        foreground=TEXT_PRIMARY,
        font=FONT_TITLE,
    )
    style.configure(
        "SubHeader.TLabel",
        background=BG_APP,
        foreground=TEXT_SECONDARY,
        font=FONT_SUBHEADER,
    )
    style.configure(
        "CardHeader.TLabel",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        font=FONT_SECTION,
    )
    style.configure(
        "Secondary.TLabel",
        background=BG_CARD,
        foreground=TEXT_SECONDARY,
        font=FONT_SMALL,
    )
    style.configure(
        "SecondaryApp.TLabel",
        background=BG_APP,
        foreground=TEXT_SECONDARY,
        font=FONT_SMALL,
    )

    # Card Containers (TLabelframe)
    style.configure(
        "TLabelframe",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        bordercolor=BORDER_SUBTLE,
        darkcolor=BORDER_SUBTLE,
        lightcolor=BORDER_SUBTLE,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        font=FONT_SECTION,
    )

    # App-level LabelFrame (if placed directly on BG_APP)
    style.configure(
        "App.TLabelframe",
        background=BG_APP,
        foreground=TEXT_PRIMARY,
        bordercolor=BORDER_SUBTLE,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "App.TLabelframe.Label",
        background=BG_APP,
        foreground=TEXT_PRIMARY,
        font=FONT_SECTION,
    )

    # Buttons: Primary (Accent)
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground=TEXT_DARK,
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor=ACCENT_HOVER,
        padding=(12, 6),
    )
    style.map(
        "Primary.TButton",
        background=[
            ("disabled", BG_INPUT),
            ("pressed", ACCENT_PRESSED),
            ("active", ACCENT_HOVER),
        ],
        foreground=[
            ("disabled", TEXT_MUTED),
            ("pressed", TEXT_DARK),
            ("active", TEXT_DARK),
        ],
    )

    # Buttons: Secondary (Neutral Raised)
    style.configure(
        "Secondary.TButton",
        background=BG_INPUT,
        foreground=TEXT_PRIMARY,
        font=FONT_BODY,
        borderwidth=1,
        bordercolor=BORDER_SUBTLE,
        focuscolor=BORDER_FOCUS,
        padding=(10, 5),
    )
    style.map(
        "Secondary.TButton",
        background=[
            ("disabled", BG_CARD),
            ("pressed", BORDER_SUBTLE),
            ("active", "#303048"),
        ],
        foreground=[
            ("disabled", TEXT_MUTED),
            ("active", TEXT_PRIMARY),
        ],
        bordercolor=[
            ("active", ACCENT),
            ("focus", ACCENT),
        ],
    )

    # Buttons: Small toolbar buttons (e.g., Export, Clear)
    style.configure(
        "Small.TButton",
        background=BG_INPUT,
        foreground=TEXT_SECONDARY,
        font=FONT_SMALL,
        borderwidth=1,
        bordercolor=BORDER_SUBTLE,
        padding=(6, 2),
    )
    style.map(
        "Small.TButton",
        background=[
            ("disabled", BG_CARD),
            ("active", "#303048"),
        ],
        foreground=[
            ("disabled", TEXT_MUTED),
            ("active", TEXT_PRIMARY),
        ],
    )

    # Default TButton fallback
    style.configure(
        "TButton",
        background=BG_INPUT,
        foreground=TEXT_PRIMARY,
        font=FONT_BODY,
        borderwidth=1,
        bordercolor=BORDER_SUBTLE,
        padding=(8, 4),
    )
    style.map(
        "TButton",
        background=[("active", "#303048"), ("disabled", BG_CARD)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    # Entry Fields
    style.configure(
        "TEntry",
        fieldbackground=BG_INPUT,
        foreground=TEXT_PRIMARY,
        insertcolor=TEXT_PRIMARY,
        bordercolor=BORDER_SUBTLE,
        lightcolor=BORDER_SUBTLE,
        darkcolor=BORDER_SUBTLE,
        padding=5,
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", BG_CARD)],
        foreground=[("disabled", TEXT_MUTED)],
        bordercolor=[("focus", ACCENT)],
    )

    # Spinbox
    style.configure(
        "TSpinbox",
        fieldbackground=BG_INPUT,
        foreground=TEXT_PRIMARY,
        background=BG_INPUT,
        arrowcolor=TEXT_SECONDARY,
        bordercolor=BORDER_SUBTLE,
        darkcolor=BORDER_SUBTLE,
        lightcolor=BORDER_SUBTLE,
        padding=4,
    )
    style.map(
        "TSpinbox",
        fieldbackground=[("disabled", BG_CARD)],
        foreground=[("disabled", TEXT_MUTED)],
        arrowcolor=[("active", ACCENT), ("disabled", TEXT_MUTED)],
        bordercolor=[("focus", ACCENT)],
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=BG_INPUT,
        foreground=TEXT_PRIMARY,
        background=BG_INPUT,
        arrowcolor=TEXT_SECONDARY,
        bordercolor=BORDER_SUBTLE,
        darkcolor=BORDER_SUBTLE,
        lightcolor=BORDER_SUBTLE,
        padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG_INPUT), ("disabled", BG_CARD)],
        foreground=[("disabled", TEXT_MUTED)],
        arrowcolor=[("active", ACCENT), ("disabled", TEXT_MUTED)],
        bordercolor=[("focus", ACCENT)],
    )

    # Checkbutton
    style.configure(
        "TCheckbutton",
        background=BG_CARD,
        foreground=TEXT_SECONDARY,
        font=FONT_SMALL,
    )
    style.map(
        "TCheckbutton",
        background=[("active", BG_CARD)],
        foreground=[("active", TEXT_PRIMARY)],
    )

    # Treeview (Data tables and KV lists)
    style.configure(
        "Treeview",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG_CARD,
        bordercolor=BORDER_SUBTLE,
        borderwidth=0,
        font=FONT_BODY,
        rowheight=26,
    )
    style.map(
        "Treeview",
        background=[("selected", "#2e3440")],
        foreground=[("selected", TEXT_PRIMARY)],
    )
    style.configure(
        "Treeview.Heading",
        background=BG_INPUT,
        foreground=TEXT_PRIMARY,
        font=FONT_SMALL_BOLD,
        bordercolor=BORDER_SUBTLE,
        borderwidth=1,
        padding=(6, 4),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", "#32324a")],
        foreground=[("active", ACCENT)],
    )

    # Progressbar
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=BG_INPUT,
        background=ACCENT,
        bordercolor=BORDER_SUBTLE,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        troughcolor=BG_CARD,
        background=BG_INPUT,
        bordercolor=BORDER_SUBTLE,
        arrowcolor=TEXT_SECONDARY,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", BORDER_SUBTLE)],
        arrowcolor=[("active", ACCENT)],
    )

    # PanedWindow
    style.configure("TPanedwindow", background=BG_APP)

    return style
