"""Executed by the fresh wheel venv from a copied external directory."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from spice_lineage import __version__, cli
from spice_lineage.paths import PACKAGE_DIR, R_DIR
from spice_lineage.runtime_info import capture_runtime
from standard_example import assert_standard_example

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "expected.json").read_text())
SPICE = shutil.which("spice")


def run(*args, expected_code=0):
    result = subprocess.run([SPICE, *map(str, args)], text=True,
                            capture_output=True, timeout=120)
    if result.returncode != expected_code:
        raise AssertionError(f"{result.args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result


class InstalledPackageTests(unittest.TestCase):
    def test_metadata_resources_and_import_location(self):
        dist = importlib.metadata.distribution("spice-lineage")
        self.assertEqual(dist.version, __version__)
        self.assertEqual(__version__, EXPECTED["version"])
        self.assertTrue(PACKAGE_DIR.is_relative_to(Path(sys.prefix)))
        self.assertIn("site-packages", PACKAGE_DIR.parts)
        self.assertFalse(PACKAGE_DIR.is_relative_to(Path(EXPECTED["source_root"])))
        self.assertIsNone(importlib.util.find_spec("scripts"))
        self.assertIsNone(importlib.util.find_spec("SPICE"))
        entry = next(e for e in dist.entry_points if e.group == "console_scripts" and e.name == "spice")
        self.assertIs(entry.load(), cli.main)
        actual = {p.relative_to(PACKAGE_DIR).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in PACKAGE_DIR.rglob("*") if p.is_file() and p.suffix in (".py", ".R")}
        self.assertEqual(actual, EXPECTED["source_hashes"])
        self.assertEqual({p.name for p in R_DIR.glob("*.R")}, set(EXPECTED["r_files"]))
        files = [str(f) for f in dist.files]
        for name in ("LICENSE",):
            self.assertTrue(any(f.endswith("/licenses/" + name) for f in files))
        direct_url = json.loads(dist.read_text("direct_url.json"))
        self.assertNotIn("dir_info", direct_url)  # A wheel archive, never editable.
        print(f"Installed import: {PACKAGE_DIR / '__init__.py'}", flush=True)

    def test_version_help_and_exit_codes(self):
        self.assertEqual(run("--version").stdout.strip(), "SPICE " + EXPECTED["version"])
        self.assertIn("usage: spice", run("--help").stdout)
        choices = next(a.choices for a in cli.build_parser()._actions
                       if isinstance(a, argparse._SubParsersAction))
        self.assertEqual(set(choices), set(EXPECTED["subcommands"]))
        for command in choices:
            with self.subTest(command=command):
                self.assertIn("usage: spice " + command, run(command, "--help").stdout)
        run(expected_code=2)
        run("unknown-command", expected_code=2)

    def test_real_standard_filter_and_legacy_equivalence(self):
        out = HERE / "wheel output with spaces"
        run("filter", HERE / "standard", out, "example", "--input_format", "standard",
            "--min_alt_cells_per_snv", "2", "--min_snvs_per_cell", "1", "--threads", "1")
        assert_standard_example(self, out, EXPECTED["version"])
        for suffix in (".SNV_mat.filter.csv", ".SNV_mat.filter.fasta", ".cellID.filter.csv",
                       ".selected_cells.tsv", ".SNV_mat.input.tsv", ".SNVs.filter.csv"):
            self.assertEqual((out / ("example" + suffix)).read_bytes(),
                             (HERE / "legacy output" / ("example" + suffix)).read_bytes())
        record = json.loads((out / "example.runtime.json").read_text())
        self.assert_provenance(record)

    def assert_provenance(self, record):
        self.assertEqual(record["spice_version"], EXPECTED["version"])
        self.assertEqual(record["source_root"], str(PACKAGE_DIR))
        for field in ("git_commit", "git_status"):
            self.assertIn("unavailable", record[field])
            self.assertNotIn("output", record[field])
        self.assertEqual(set(record["source_sha256"]),
                         {"spice_lineage/" + path for path in EXPECTED["source_hashes"]}
                         | {"spice_lineage/VERSION"})
        self.assertEqual(record["source_sha256"]["spice_lineage/VERSION"],
                         hashlib.sha256((PACKAGE_DIR / "VERSION").read_bytes()).hexdigest())
        for path, digest in EXPECTED["source_hashes"].items():
            self.assertEqual(record["source_sha256"]["spice_lineage/" + path], digest)

    def test_provenance_in_unrelated_repository(self):
        parent = HERE / "unrelated"
        parent.mkdir()
        subprocess.run(["git", "init", "-q", str(parent)], check=True)
        # Deliberately direct ambient Git discovery at another repository.
        old = Path.cwd()
        try:
            os.chdir(parent)
            from unittest.mock import patch
            with patch.dict(os.environ, {"GIT_DIR": str(parent / ".git"),
                                        "GIT_WORK_TREE": str(parent)}):
                record = capture_runtime(argparse.Namespace(command="summarize"), PACKAGE_DIR)
            self.assert_provenance(record)
        finally:
            os.chdir(old)

    def test_summary_equivalence_and_overwrite_protection(self):
        out = HERE / "wheel-summary.tsv"
        run("summarize", HERE / "manifest.tsv", out)
        self.assertEqual(out.read_bytes(), (HERE / "legacy-summary.tsv").read_bytes())
        self.assert_provenance(json.loads(Path(str(out) + ".runtime.json").read_text()))
        run("summarize", HERE / "manifest.tsv", out, expected_code=2)
        records = list(HERE.glob("wheel-summary.tsv.runtime*.json"))
        self.assertEqual(len(records), 2)
        self.assertEqual({json.loads(p.read_text())["success"] for p in records}, {True, False})


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(InstalledPackageTests))
    if not result.wasSuccessful() or result.skipped or result.testsRun != 5:
        raise SystemExit(1)
