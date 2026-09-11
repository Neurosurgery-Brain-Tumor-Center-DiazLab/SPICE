"""Fast packaging consistency and unsafe/incomplete container-lock regressions."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

from spice_lineage import cli

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("distribution", ROOT / "scripts/check_distribution.py")
distribution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(distribution)


class DistributionTests(unittest.TestCase):
    def test_recipe_identity_source_and_dependencies(self):
        recipe = (distribution.RECIPE / "meta.yaml").read_text()
        version = (ROOT / "VERSION").read_text().strip()
        self.assertIn('version: "' + version + '"', recipe)
        self.assertIn("name: spice-lineage", recipe)
        self.assertIn("license: GPL-3.0-only", recipe)
        self.assertIn("license_file: LICENSE", recipe)
        self.assertIn("noarch: python", recipe)
        self.assertIn("number: 0", recipe)
        self.assertRegex(recipe, r"sha256: [0-9a-f]{64}\n")
        self.assertIn("/archive/" + distribution.SOURCE_REVISION + ".tar.gz", recipe)
        run_section = recipe.split("  run:\n", 1)[1].split("\ntest:", 1)[0]
        dependencies = {line.strip().split()[1] for line in run_section.splitlines() if line.strip()}
        r_names = set()
        for path in (ROOT / "spice_lineage/resources/r").glob("*.R"):
            text = path.read_text()
            r_names.update(re.findall(r"^library\((\w+)\)", text, re.M))
            match = re.search(r"required_pkgs <- c\(([^)]+)\)", text)
            if match:
                r_names.update(re.findall(r'"(\w+)"', match[1]))
        r_names -= {"parallel"}
        expected = {"r-" + name if name != "ggtree" else "bioconductor-ggtree" for name in r_names}
        self.assertEqual(dependencies, expected | {"python", "pandas", "r-base", "iqtree"})
        self.assertIn("setuptools >=77", recipe)
        self.assertIn("python >=3.10,<4", recipe)
        self.assertIn("pandas >=1.5,<3", recipe)
        self.assertIn("r-base >=4.3.3,<4.4.0a0", recipe)
        self.assertIn("iqtree >=2.4,<3", recipe)
        self.assertIn("--no-deps --no-build-isolation --no-cache-dir", recipe)
        commands = next(a.choices for a in cli.build_parser()._actions
                        if isinstance(a, argparse._SubParsersAction))
        self.assertEqual(set(commands), set(distribution.SUBCOMMANDS))
        for name in commands:
            self.assertIn("spice " + name + " --help", recipe)

    def test_workflow_is_manual_and_never_publishes(self):
        workflow = (ROOT / ".github/workflows/distribution.yml").read_text()
        self.assertEqual(workflow.split("\non:\n")[1].split("\npermissions:")[0].strip(),
                         "workflow_dispatch:")
        self.assertIn("contents: read", workflow)
        self.assertIn("ubuntu-24.04", workflow)
        self.assertNotIn("--conda-only", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("docker push", workflow)
        actions = re.findall(r"uses: (\S+)", workflow)
        self.assertEqual(len(actions), 3)
        self.assertTrue(all(re.search(r"@[0-9a-f]{40}$", action) for action in actions))
        self.assertIn("name: Phase 1 required checks", (ROOT / ".github/workflows/ci.yml").read_text())

    def test_container_metadata_and_clean_context(self):
        text = distribution.CONTAINERFILE.read_text()
        self.assertRegex(text, r"ARG BASE_IMAGE=[^\s]+@sha256:[0-9a-f]{64}\n")
        self.assertIn("ARG SPICE_VERSION=" + (ROOT / "VERSION").read_text().strip(), text)
        self.assertIn("ARG SOURCE_REVISION=" + distribution.SOURCE_REVISION, text)
        self.assertIn("ENTRYPOINT []", text)
        self.assertNotIn("latest", text)
        self.assertNotIn("COPY . ", text)
        self.assertNotIn("BayesTraitsV4", text)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "spice-lineage-0.2.0-py_0.conda"
            package.write_bytes(b"synthetic package for context validation")
            records = [
                {"name": "spice-lineage", "sha256": distribution.sha256(package)},
                {"name": "python", "sha256": "a" * 64,
                 "url": "https://conda.anaconda.org/conda-forge/linux-64/python.conda"},
            ]
            context = distribution.make_container_context(root, package, records)
            actual = {p.relative_to(context).as_posix() for p in context.rglob("*") if p.is_file()}
            self.assertEqual(actual, {"Containerfile", "runtime-linux-64.lock",
                                      "channel/noarch/" + package.name})
            lock = (context / "runtime-linux-64.lock").read_text()
            self.assertIn("file:///tmp/channel/noarch/" + package.name, lock)
            self.assertNotIn(str(root), lock)

    def test_container_lock_rejects_unverified_and_external_packages(self):
        for case in ("bad_source", "no_hash", "wrong_local_hash", "missing_spice"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                package = root / "spice-lineage-0.2.0-py_0.conda"
                package.write_bytes(b"fixture")
                records = [{"name": "spice-lineage", "sha256": distribution.sha256(package)}]
                if case == "bad_source":
                    records.append({"name": "unexpected", "sha256": "a" * 64,
                                    "url": "https://unapproved.invalid/package.conda"})
                elif case == "no_hash":
                    records[0].pop("sha256")
                elif case == "wrong_local_hash":
                    records[0]["sha256"] = "a" * 64
                else:
                    records = []
                with self.assertRaises(RuntimeError):
                    distribution.make_container_context(root, package, records)

    def test_toolchain_lock_is_explicit_and_hash_pinned(self):
        lines = (ROOT / "ci/distribution-linux-64.lock").read_text().splitlines()
        entries = [line for line in lines if line and not line.startswith("#")]
        self.assertEqual(entries[0], "@EXPLICIT")
        self.assertTrue(all(re.fullmatch(
            r"https://conda.anaconda.org/conda-forge/(linux-64|noarch)/[^#]+#[0-9a-f]{64}", line)
                            for line in entries[1:]))
        self.assertGreater(len(entries), 20)


if __name__ == "__main__":
    unittest.main()
