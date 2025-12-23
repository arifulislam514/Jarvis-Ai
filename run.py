"""Convenience entry point.

Use this if you prefer:
    python run.py

It simply executes Main.py.
"""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    main_path = Path(__file__).with_name("Main.py")
    runpy.run_path(str(main_path), run_name="__main__")
