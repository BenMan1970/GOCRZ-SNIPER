"""Bluestar Sniper entry point (Streamlit)."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# Make sure the package is importable regardless of the working directory used
# by the host (Streamlit Cloud, local, etc.).
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Fallback: search parent directories for a 'bluestar' package.
if not os.path.isdir(os.path.join(_HERE, "bluestar")):
    for parent in (_HERE, os.path.dirname(_HERE)):
        for root, dirs, _ in os.walk(parent):
            if "bluestar" in dirs and os.path.isfile(
                os.path.join(root, "bluestar", "__init__.py")
            ):
                if root not in sys.path:
                    sys.path.insert(0, root)
                break

from bluestar.ui.app import main

main()
