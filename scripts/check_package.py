#!/usr/bin/env python3
"""Build an sdist/wheel and exercise a non-editable install outside this checkout."""
import argparse
import configparser
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
R_FILES = {
    "matrix_bridge.R", "mutation_filter.R", "BranchSupportCut.R",
    "ancestry_core.R", "plasticity_core.R",
    "spice_ancestry_utils.R", "spice_plasticity_utils.R",
}
PY_FILES = {
    "__init__.py", "cli.py", "paths.py", "runtime_info.py", "standard_input.py",
    "import_monopogen.py", "convert_matrix_to_fasta.py", "IQTREE2.py", "summarize_clones.py",
}


def run(command, cwd, env):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True, timeout=600)


def inspect_artifacts(wheel, sdist):
    version = (ROOT / "VERSION").read_text().strip()
    package_files = ({"spice_lineage/" + p for p in PY_FILES} |
                     {"spice_lineage/resources/r/" + p for p in R_FILES} |
                     {"spice_lineage/VERSION"})
    info = "spice_lineage-" + version + ".dist-info/"
    wheel_files = package_files | {info + p for p in (
    "METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt",
    "licenses/LICENSE")}
    with zipfile.ZipFile(wheel) as archive:
        actual = set(archive.namelist())
        if actual != wheel_files:
            raise AssertionError(f"Unexpected wheel contents: {actual ^ wheel_files}")
        metadata = BytesParser().parsebytes(archive.read(info + "METADATA"))
        assert metadata["Name"] == "spice-lineage"
        assert metadata["Version"] == version
        assert metadata["Requires-Python"] == ">=3.10"
        assert metadata["License-Expression"] == "GPL-3.0-only"
        assert metadata.get_all("Requires-Dist") == ["pandas<3,>=1.5"]
        assert archive.read("spice_lineage/VERSION").decode().strip() == version
        entries = configparser.ConfigParser()
        entries.read_string(archive.read(info + "entry_points.txt").decode())
        assert dict(entries["console_scripts"]) == {"spice": "spice_lineage.cli:main"}
        for name in package_files | {
    info + "licenses/LICENSE",
}:
            local = ROOT / (Path(name).name if "/licenses/" in name else name)
            assert archive.read(name) == local.read_bytes(), name
    # A source distribution includes development checks and their synthetic fixtures,
    # but only the explicitly listed legacy merge helper needed by those checks.
    source_files = package_files | {
        "pyproject.toml", "MANIFEST.in", "SPICE.py", "VERSION", "LICENSE", "CITATION.cff",
        "README.md", "CHANGELOG.md", "SPICE.png", "requirements.txt", "environment.yml",
        "scripts/check_ci.py", "scripts/check_package.py", "scripts/check_ci_dependencies.R",
        "scripts/monopogen_merge.R", "scripts/install_R_dependencies.R", ".github/workflows/ci.yml",
        "examples/README.md", "examples/standard/matrix.tsv", "examples/standard/cells.tsv",
        "examples/standard/variants.tsv", "ci/environment.yml", "ci/linux-64.lock",
        "ci/requirements-build.txt", "ci/integration-environment.yml",
        "ci/integration-linux-64.lock", "scripts/check_integration.py",
        ".github/workflows/integration.yml", ".github/workflows/distribution.yml",
        "scripts/check_distribution.py", "ci/distribution-environment.yml",
        "ci/distribution-linux-64.lock",
    }
    for pattern in ("docs/*.md", "tests/*.py", "tests/*.R",
                    "tests/integration/**/*.py", "tests/integration/**/*.R",
                    "tests/integration/**/*.md", "tests/integration/**/*.tsv",
                    "tests/integration/**/*.nwk", "tests/distribution/**/*.py",
                    "tests/distribution/**/*.md", "tests/distribution/**/*.nwk",
                    "packaging/**/*.yaml", "packaging/**/*.md", "packaging/**/Containerfile"):
        source_files.update(p.relative_to(ROOT).as_posix() for p in ROOT.glob(pattern))
    generated = {"PKG-INFO", "setup.cfg"} | {"spice_lineage.egg-info/" + p for p in (
        "PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt",
        "requires.txt", "top_level.txt")}
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        assert all(m.isdir() or m.isfile() for m in members)
        prefix = "spice_lineage-" + version + "/"
        actual = {m.name.removeprefix(prefix) for m in members if m.isfile()}
        assert actual == source_files | generated, actual ^ (source_files | generated)
        for name in source_files:
            assert archive.extractfile(prefix + name).read() == (ROOT / name).read_bytes(), name
    print(f"Artifact contents verified: {len(wheel_files)} wheel files; "
          f"{len(source_files | generated)} sdist files", flush=True)


def check(work):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH" and not k.startswith("GIT_")}
    env["PYTHONNOUSERSITE"] = "1"
    neutral = work / "neutral directory"
    neutral.mkdir()
    # Prove the initial test location is not contained in any Git checkout.
    git = subprocess.run(["git", "-C", str(neutral), "rev-parse", "--show-toplevel"],
                         env=env, capture_output=True)
    assert git.returncode != 0, "Package checks require an external directory outside Git"
    dist = work / "dist"
    # Default build creates the wheel from the sdist, covering both release paths.
    run([sys.executable, "-m", "build", "--outdir", dist, ROOT], work, env)
    wheels, sdists = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1
    inspect_artifacts(wheels[0], sdists[0])
    prefix = work / "venv"
    venv.EnvBuilder(with_pip=True).create(prefix)
    python = prefix / "bin/python"
    run([python, "-m", "pip", "install", wheels[0]], neutral, env)
    run([python, "-m", "pip", "check"], neutral, env)
    shutil.copytree(ROOT / "examples/standard", neutral / "standard")
    for name in ("installed_checks.py", "standard_example.py"):
        shutil.copyfile(ROOT / "tests" / name, neutral / name)
    sys.path.insert(0, str(ROOT))
    from spice_lineage import cli
    package = ROOT / "spice_lineage"
    expected = {
        "version": (ROOT / "VERSION").read_text().strip(),
        "source_root": str(ROOT),
        "r_files": sorted(R_FILES),
        "source_hashes": {p.relative_to(package).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in package.rglob("*") if p.is_file() and p.suffix in (".py", ".R")},
        "subcommands": list(next(a.choices for a in cli.build_parser()._actions
                                if isinstance(a, argparse._SubParsersAction))),
    }
    (neutral / "expected.json").write_text(json.dumps(expected, indent=2))
    run([sys.executable, ROOT / "SPICE.py", "filter", neutral / "standard",
         neutral / "legacy output", "example", "--input_format", "standard",
         "--min_alt_cells_per_snv", "2", "--min_snvs_per_cell", "1", "--threads", "1"],
        neutral, env)
    (neutral / "manifest.tsv").write_text(
        "clone_id\tplasticity_test\nA\ta.tsv\nB\tb.tsv\nC\tmissing.tsv\n")
    header = ("test_status\tobserved_plasticity\tempirical_p\talternative\t"
              "n_permutations_requested\tn_permutations_successful\n")
    (neutral / "a.tsv").write_text(header + "pass\t12\t0.01\tgreater\t1000\t1000\n")
    (neutral / "b.tsv").write_text(header + "incomplete\t12\tNA\tgreater\t1000\t0\n")
    run([sys.executable, ROOT / "SPICE.py", "summarize", neutral / "manifest.tsv",
         neutral / "legacy-summary.tsv"], neutral, env)
    env["PATH"] = str(prefix / "bin") + os.pathsep + env["PATH"]
    run([python, neutral / "installed_checks.py"], neutral, env)
    run([python, "-m", "pip", "list"], neutral, env)
    print(f"PASS: package checks; wheel={wheels[0]}; sdist={sdists[0]}; install={prefix}",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, help="New external directory; retain artifacts and evidence")
    args = parser.parse_args()
    if args.work_dir:
        work = args.work_dir.resolve()
        if work.is_relative_to(ROOT):
            parser.error("--work-dir must be outside the source checkout")
        work.mkdir(parents=True, exist_ok=False)
        check(work)
    else:
        with tempfile.TemporaryDirectory(prefix="SPICE package ") as tmp:
            check(Path(tmp))


if __name__ == "__main__":
    main()
