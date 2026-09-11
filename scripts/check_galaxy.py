#!/usr/bin/env python3
"""Manual Linux Galaxy validation against an unpublished local SPICE Conda build."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

from check_distribution import inspect_package, prepare_checks, sha256
from check_integration import bayestraits, BT_ARCHIVE_SHA256, BT_BINARY_SHA256

ROOT = Path(__file__).resolve().parents[1]
PLANEMO_VERSION = "0.75.47"
GALAXY_COMMIT = "ec10c792f94c6da0bc97b177f73be2a9287637dd"
IQTREE_REVISION = "e727e82945af"
IQTREE_TOOL_VERSION = "2.4.0+galaxy2"
IQTREE_REPOSITORY_ID = "a242fbfe4befb19a"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(command, work, env, name, report, timeout=5400):
    command = list(map(str, command))
    print("+ " + " ".join(command), flush=True)
    path = work / (name + ".log")
    started = time.monotonic()
    with path.open("w") as log:
        result = subprocess.run(command, cwd=work, env=env, text=True,
                                stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    report["commands"].append({"stage": name, "argv": command, "exit_code": result.returncode,
                               "seconds": round(time.monotonic() - started, 2), "log": str(path)})
    output = path.read_text(errors="replace")
    if result.returncode:
        print(output[-12000:], flush=True)
        raise RuntimeError(f"{name} failed ({result.returncode}); see {path}")
    return output


def validate_test_report(path, expected):
    data = json.loads(path.read_text())
    tests = data.get("tests", [])
    require(len(tests) == expected, f"Expected {expected} required tests in {path}; found {len(tests)}")
    states = [test.get("data", {}).get("status") for test in tests]
    require(all(state == "success" for state in states), f"Required test did not succeed: {states}")
    return {"status": "pass", "tests": len(tests), "skipped": 0,
            "identifiers": [test.get("id") for test in tests], "report": str(path)}


def verify_iqtree_revision():
    url = ("https://toolshed.g2.bx.psu.edu/api/repositories/" + IQTREE_REPOSITORY_ID
           + "/metadata?downloadable_only=true")
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    revisions = [v for v in metadata.values() if v.get("changeset_revision") == IQTREE_REVISION]
    require(len(revisions) == 1, "Pinned IQ-TREE Tool Shed revision is unavailable; do not switch to IQ-TREE 3")
    revision = revisions[0]
    require(revision.get("downloadable") and not revision.get("malicious"), "IQ-TREE revision is not installable")
    tool = next(t for t in revision["tools"] if t["id"] == "iqtree")
    require(tool["version"] == IQTREE_TOOL_VERSION and
            tool["requirements"] == [{"name": "iqtree", "type": "package", "version": "2.4.0"}],
            "Pinned IQ-TREE tool version/dependency differs from the validated contract")
    return {"owner": "iuc", "repository": "iqtree", "revision": IQTREE_REVISION,
            "tool_version": IQTREE_TOOL_VERSION, "package_version": "2.4.0",
            "profile": tool["profile"], "downloadable": True, "source": url}


def check(args, work, report):
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "Linux x86_64 required")
    require(not work.is_relative_to(ROOT) and " " not in str(work), "Use an external work directory without spaces")
    require(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=work,
                           capture_output=True).returncode != 0, "Work directory must be outside Git")
    planemo = args.planemo.expanduser().resolve()
    conda_prefix = args.conda_prefix.expanduser().resolve()
    require(planemo.is_file(), "Install the pinned ci/requirements-galaxy.txt toolchain first")
    home = work / "home"
    home.mkdir()
    env = {"PATH": str(planemo.parent) + ":" + str(conda_prefix / "bin") + ":/usr/bin:/bin",
           "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
           "PYTHONNOUSERSITE": "1", "PYTHONUNBUFFERED": "1",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "CONDA_CHANNEL_PRIORITY": "strict", "CONDA_SOLVER": "libmamba",
           "CONDA_ANACONDA_UPLOAD": "false",
           "PIP_BUILD_CONSTRAINT": str(ROOT / "ci/galaxy-build-constraints.txt")}
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    report["planemo"] = run([planemo, "--version"], work, env, "planemo-version", report, 60).strip()
    require(report["planemo"] == f"planemo, version {PLANEMO_VERSION}", "Unexpected Planemo version")
    report["checkout_commit"] = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    report["spice_version"] = (ROOT / "VERSION").read_text().strip()
    staged = work / "galaxy"
    shutil.copytree(ROOT / "galaxy", staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    tools = staged / "tools"
    workflow = staged / "workflows/spice_lineage_analysis.ga"
    for name, command in [
        ("lint", [planemo, "lint", tools]),
        ("shed-lint", [planemo, "shed_lint", tools]),
        ("workflow-lint", [planemo, "workflow_lint", workflow]),
    ]:
        run(command, work, env, name, report, 300)
    report["lint"] = "pass"
    report["iqtree"] = verify_iqtree_revision()
    if args.lint_only:
        report.update(status="incomplete", complete=False,
                      pending=["local Conda package", "Galaxy wrapper tests", "end-to-end workflow"])
        print("INCOMPLETE: lint passed; functional Galaxy tests have not run.", flush=True)
        return

    require((conda_prefix / "bin/conda").is_file(), "Activate the Phase 5 distribution toolchain")
    distribution_result = args.distribution_result
    if distribution_result is None:
        distribution_work = work / "distribution"
        # The existing Phase 5 runner proves the package and clean installation.
        run([conda_prefix / "bin/python", ROOT / "scripts/check_distribution.py", "--conda-only",
             "--work-dir", distribution_work], work, env, "distribution", report)
        distribution_result = distribution_work / "result.json"
    distribution_result = distribution_result.resolve()
    distribution = json.loads(distribution_result.read_text())
    require(distribution["conda_checks"]["status"] == "pass" and
            distribution["conda_checks"]["skipped"] == 0 and not distribution["published"],
            "Local Conda evidence is incomplete or not an unpublished build")
    package = Path(distribution["package"]).resolve(strict=True)
    require(sha256(package) == distribution["package_sha256"], "Local package checksum mismatch")
    inspection = work / "package-check"
    inspection.mkdir()
    _, _, expected = prepare_checks(inspection)
    inspect_package(package, inspection, expected)
    channel = package.parent.parent
    require((channel / "noarch/repodata.json").is_file(), "Local Conda channel is not indexed")
    report["local_conda"] = {"package": str(package), "sha256": sha256(package),
                             "channel": channel.as_uri(), "version": distribution["spice_version"],
                             "payload_matches_checkout": True, "distribution_result": str(distribution_result)}

    galaxy_root = args.galaxy_root.resolve() if args.galaxy_root else work / "galaxy-source"
    if args.galaxy_root is None:
        run(["git", "init", galaxy_root], work, env, "galaxy-init", report, 60)
        run(["git", "-C", galaxy_root, "remote", "add", "origin", "https://github.com/galaxyproject/galaxy.git"], work, env, "galaxy-origin", report, 60)
        run(["git", "-C", galaxy_root, "fetch", "--depth=1", "origin", GALAXY_COMMIT], work, env, "galaxy-fetch", report, 600)
        run(["git", "-C", galaxy_root, "checkout", "--detach", "FETCH_HEAD"], work, env, "galaxy-checkout", report, 300)
    revision = run(["git", "-C", galaxy_root, "rev-parse", "HEAD"], work, env, "galaxy-revision", report, 60).strip()
    require(revision == GALAXY_COMMIT, "Galaxy checkout does not match the pinned 25.0 release-branch commit")
    run(["git", "-C", galaxy_root, "diff", "--exit-code", "HEAD"], work, env, "galaxy-source-clean", report, 60)
    version_text = (galaxy_root / "lib/galaxy/version.py").read_text()
    versions = dict(re.findall(r'^(VERSION_MAJOR|VERSION_MINOR) = "([^"\n]+)"', version_text, re.M))
    require(versions.get("VERSION_MAJOR") == "25.0", "Unexpected Galaxy major/minor")
    report["galaxy"] = {"commit": revision, "version": versions["VERSION_MAJOR"] + "." + versions["VERSION_MINOR"], "profile": "25.0"}
    print(json.dumps({key: report[key] for key in ("planemo", "galaxy", "iqtree", "local_conda")}, indent=2), flush=True)
    # Pin pip explicitly so build constraints apply inside isolated dependency builds.
    galaxy_venv = work / "galaxy-venv"
    run([planemo.parent / "python", "-m", "venv", galaxy_venv], work, env, "galaxy-venv", report, 180)
    run([galaxy_venv / "bin/python", "-m", "pip", "install", "pip==26.2.1"],
        work, env, "galaxy-pip", report, 300)
    env["GALAXY_VIRTUAL_ENV"] = str(galaxy_venv)
    report["galaxy"]["bootstrap_pip"] = "26.2.1"
    common = ["--galaxy_root", galaxy_root, "--galaxy_python_version", "3.11",
              "--galaxy_startup_timeout", "1200", "--conda_prefix", conda_prefix,
              "--conda_channels", channel.as_uri() + ",conda-forge,bioconda",
              "--conda_dependency_resolution", "--conda_auto_install", "--no_conda_auto_init",
              "--job_workers", "1", "--no_cleanup"]
    binary = None
    try:
        with tempfile.TemporaryDirectory(prefix="spice-galaxy-bayestraits-") as temporary:
            binary, info = bayestraits(Path(temporary), env)
            require(info["sha256"] == BT_BINARY_SHA256 and info["archive_sha256"] == BT_ARCHIVE_SHA256,
                    "Galaxy tests require the verified official BayesTraits V4.1.3 download")
            report["bayestraits"] = info
            env["BAYESTRAITS_BIN"] = str(binary)
            expected_tools = sum(len(ET.parse(path).getroot().findall("tests/test"))
                                 for path in tools.glob("spice_*.xml"))
            for name, target, count, extra in [("tools", tools, expected_tools, []),
                                               ("workflow", workflow, 1, ["--extra_tools", tools])]:
                test_report = work / (name + ".json")
                run([planemo, "test", target, *common, *extra,
                     "--test_output", work / (name + ".html"),
                     "--test_output_json", test_report,
                     "--test_output_xunit", work / (name + ".xml")],
                    work, env, name, report)
                report[name] = validate_test_report(test_report, count)
    finally:
        if binary is not None:
            report["bayestraits_removed"] = not binary.exists()
            require(report["bayestraits_removed"], "Temporary BayesTraits executable was not removed")
    report.update(status="pass", complete=True, skipped=0)
    print("PASS: all Galaxy wrapper and end-to-end workflow tests; zero skips; nothing published", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="New external directory; evidence is retained")
    parser.add_argument("--planemo", type=Path, default=Path(shutil.which("planemo") or "planemo"))
    parser.add_argument("--conda-prefix", type=Path, default=Path(sys.prefix))
    parser.add_argument("--galaxy-root", type=Path, help="Reuse a checkout of the exact pinned Galaxy commit")
    parser.add_argument("--distribution-result", type=Path, help="Reuse verified local Phase 5 Conda evidence; payload is checked again")
    parser.add_argument("--lint-only", action="store_true", help="Report INCOMPLETE; do not claim functional acceptance")
    args = parser.parse_args()
    work = args.work_dir.expanduser().resolve()
    require(not work.is_relative_to(ROOT), "Work directory must be outside SPICE")
    work.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "complete": False, "published": False, "commands": []}
    started = time.monotonic()
    try:
        check(args, work, report)
    except Exception as exc:
        report.update(status="failed", complete=False, error=str(exc))
        print(f"FAIL: {exc}; evidence: {work}", file=sys.stderr, flush=True)
        raise
    finally:
        report["total_seconds"] = round(time.monotonic() - started, 2)
        (work / "result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
