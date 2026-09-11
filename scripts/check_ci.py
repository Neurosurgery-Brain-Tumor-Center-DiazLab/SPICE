#!/usr/bin/env python3
"""Required Phase 1 checks, shared by local Linux installations and CI."""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=ROOT, check=True, timeout=300)


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    print(f"Environment: {platform.platform()}; Python {sys.version}", flush=True)
    if platform.system() != "Linux" or sys.version_info < (3, 10):
        raise RuntimeError("Required checks need Linux and Python >= 3.10")
    if not shutil.which("Rscript"):
        raise RuntimeError("Rscript is required; skipped R integration is not a pass")
    import pandas
    print(f"pandas {pandas.__version__}", flush=True)
    run(["Rscript", "--vanilla", str(ROOT / "scripts/check_ci_dependencies.R")])

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    discovered = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"Python: discovered={discovered} run={result.testsRun} "
          f"skipped={len(result.skipped)} failures={len(result.failures)} "
          f"errors={len(result.errors)}", flush=True)
    if (not discovered or not result.wasSuccessful() or result.skipped
            or result.testsRun != discovered):
        raise RuntimeError("Required Python suite failed, skipped tests, or ran no tests")

    run(["Rscript", "--vanilla", "tests/test_mcmc_qc.R"])
    run([sys.executable, "SPICE.py", "--help"])
    version = subprocess.check_output(
        [sys.executable, "SPICE.py", "--version"], cwd=ROOT, text=True, timeout=30
    ).strip()
    expected = (ROOT / "VERSION").read_text().strip()
    if version != f"SPICE {expected}":
        raise RuntimeError(f"Unexpected version output: {version!r}")
    print(version, flush=True)

    import SPICE
    # Discover current commands instead of silently omitting new subcommands.
    parser = SPICE.build_parser()
    subcommands = next(a.choices for a in parser._actions
                       if isinstance(a, argparse._SubParsersAction))
    for command in subcommands:
        run([sys.executable, "SPICE.py", command, "--help"])
    print("PASS: Phase 1 checks (no real IQ-TREE or BayesTraits inference)", flush=True)


if __name__ == "__main__":
    main()