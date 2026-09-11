"""Resources in a source checkout or an unpacked, pip-installed wheel.

R scripts source sibling files, so keep their shared directory intact. Pip
installs wheels as real files; no repository or current-directory lookup is used.
"""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
R_DIR = PACKAGE_DIR / "resources" / "r"
