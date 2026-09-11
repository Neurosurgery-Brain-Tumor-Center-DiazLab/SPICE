"""Focused source-side packaging and provenance regressions."""
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import SPICE
from spice_lineage import __version__, cli
from spice_lineage.paths import PACKAGE_DIR, R_DIR
from spice_lineage.runtime_info import checkout_root, source_provenance

ROOT = Path(__file__).resolve().parents[1]
R_FILES = {
    "matrix_bridge.R", "mutation_filter.R", "BranchSupportCut.R",
    "ancestry_core.R", "plasticity_core.R",
    "spice_ancestry_utils.R", "spice_plasticity_utils.R",
}


class PackageSourceTests(unittest.TestCase):
    def test_version_and_legacy_dispatch(self):
        self.assertIs(SPICE.main, cli.main)
        self.assertIs(SPICE.build_parser, cli.build_parser)
        self.assertEqual(__version__, (ROOT / "VERSION").read_text().strip())
        citation = next(line for line in (ROOT / "CITATION.cff").read_text().splitlines()
                        if line.startswith("version:"))
        self.assertEqual(__version__, citation.split(":", 1)[1].strip())

    def test_resources_are_package_relative(self):
        self.assertEqual({p.name for p in R_DIR.glob("*.R")}, R_FILES)
        self.assertEqual(R_DIR, PACKAGE_DIR / "resources" / "r")
        self.assertIs(importlib.import_module("spice_lineage.cli").main, SPICE.main)

    def test_unrelated_parent_git_and_git_environment_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            subprocess.run(["git", "init", "-q", str(parent)], check=True)
            package = parent / "site-packages" / "spice_lineage"
            shutil.copytree(PACKAGE_DIR, package, ignore=shutil.ignore_patterns("__pycache__"))
            # Even checkout-like markers below a parent Git repository are insufficient.
            for name in ("SPICE.py", "VERSION", "pyproject.toml"):
                shutil.copyfile(ROOT / name, package.parent / name)
            with patch.dict(os.environ, {"GIT_DIR": str(ROOT / ".git"),
                                        "GIT_WORK_TREE": str(ROOT)}):
                record = source_provenance(package)
            self.assertIsNone(checkout_root(package))
            for field in ("git_commit", "git_status"):
                self.assertIn("unavailable", record[field])
            self.assertIn("spice_lineage/resources/r/mutation_filter.R", record["source_sha256"])
            self.assertNotIn("SPICE.py", record["source_sha256"])

    def test_checkout_git_environment_cannot_redirect_provenance(self):
        expected = ROOT if (ROOT / ".git").exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            unrelated = Path(tmp)
            subprocess.run(["git", "init", "-q", str(unrelated)], check=True)
            with patch.dict(os.environ, {"GIT_DIR": str(unrelated / ".git"),
                                        "GIT_WORK_TREE": str(unrelated)}):
                self.assertEqual(checkout_root(PACKAGE_DIR), expected)


if __name__ == "__main__":
    unittest.main()
