"""ByteFlow: A Comparative Platform for Classical and Quantum Max-Cut Solutions.

Entry point for launching the ByteFlow Virtual Laboratory application.
"""

import sys
from byteflow.ui.app import ByteFlowApp


def main() -> None:
    """Launch the ByteFlow Virtual Laboratory."""
    app = ByteFlowApp()
    app.mainloop()


if __name__ == "__main__":
    main()
