#!/usr/bin/env python3
"""Read-only validation of the pinned published Test Tool Shed SPICE revision."""
import argparse
import copy
import json
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

from check_distribution import sha256
from check_galaxy import (GALAXY_COMMIT, PLANEMO_VERSION, IQTREE_REVISION, require,
                          run, validate_test_report, validate_workflow_execution,
                          verify_iqtree_revision)
from check_integration import bayestraits, BT_BINARY_SHA256, BT_ARCHIVE_SHA256
from check_public_distribution import prepare_public_artifact, verify_public_install

ROOT = Path(__file__).resolve().parents[1]
SHED = "https://testtoolshed.g2.bx.psu.edu"
HOST = "testtoolshed.g2.bx.psu.edu"
OWNER = "diazlab"
NAME = "spice_lineage"
REPOSITORY_ID = "34b0910123274f01"
REVISION = "5132fb8a542e"
VERSION = "0.2.0+galaxy0"
PUBLIC_SHA256 = "42c1adce162effda9eb151c3f7ba87bd0a0dd23111f8d6f21f16f10e7bd42974"
ARCHIVE_SHA256 = "125a5180889a14186117a5e89235b8288da67e95abef3a0cb2d9804c952d19bc"
TOOL_IDS = {"spice_filter", "spice_clones", "spice_ancestry", "spice_plasticity", "spice_summarize"}
MANIFEST = ROOT / "tests/galaxy/reviewed-toolshed-archive.json"


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def get_json(url, destination):
    # Anonymous GET only: no authentication parameters, headers or credential lookup.
    with urllib.request.urlopen(url, timeout=90) as response:
        data = response.read()
    destination.write_bytes(data)
    return json.loads(data)


def validate_metadata(repository, metadata, revisions):
    require(repository.get("id") == REPOSITORY_ID and repository.get("owner") == OWNER
            and repository.get("name") == NAME, "Wrong published repository identity")
    require(not any(repository.get(k) for k in ("private", "deleted", "deprecated")),
            "Published repository is not publicly available")
    require(revisions and revisions[-1] == REVISION,
            "shed_test selects the latest revision; expected revision is no longer latest")
    matches = [m for m in metadata.values() if m.get("changeset_revision") == REVISION]
    require(len(matches) == 1, "Published changeset is missing or ambiguous")
    revision = matches[0]
    require(revision.get("repository_id") == REPOSITORY_ID and revision.get("downloadable")
            and not revision.get("malicious") and not revision.get("invalid_tools")
            and not revision.get("missing_test_components"), "Published revision is not testable")
    tools = revision.get("tools", [])
    require(len(tools) == 5 and {t["id"] for t in tools} == TOOL_IDS, "Expected five published tools")
    for tool in tools:
        require(tool["guid"] == f"{HOST}/repos/{OWNER}/{NAME}/{tool['id']}/{VERSION}",
                "Unexpected published tool GUID")
        require(tool["version"] == VERSION and str(tool["profile"]) == "25.0",
                "Published version/profile differs")
        require(tool["requirements"] == [{"name": "spice-lineage", "type": "package", "version": "0.2.0"}],
                "Published Conda requirement differs")
        require(len(tool.get("tests", [])) == (2 if tool["id"] == "spice_plasticity" else 1),
                "Published test inventory differs")
    return {t["id"]: t["guid"] for t in tools}


def read_published_metadata(work, label):
    directory = work / label
    directory.mkdir()
    repository = get_json(f"{SHED}/api/repositories/{REPOSITORY_ID}", directory / "repository.json")
    metadata = get_json(f"{SHED}/api/repositories/{REPOSITORY_ID}/metadata?downloadable_only=true",
                        directory / "metadata.json")
    revisions = get_json(f"{SHED}/api/repositories/get_ordered_installable_revisions?name={NAME}&owner={OWNER}",
                         directory / "revisions.json")
    return validate_metadata(repository, metadata, revisions)


def compare_payload(directory, manifest, strict=True):
    actual = {p.relative_to(directory).as_posix(): {"size": p.stat().st_size, "sha256": sha256(p)}
              for p in directory.rglob("*") if p.is_file() and ".hg" not in p.parts}
    expected = manifest["files"]
    require(len(expected) == 31 and manifest["reviewed_archive_sha256"] == ARCHIVE_SHA256,
            "Wrong reviewed archive manifest")
    require(all(actual.get(name) == value for name, value in expected.items()),
            "Published/installed payload differs from reviewed archive")
    extras = sorted(actual.keys() - expected.keys())
    require(not strict or not extras, "Unexpected files in published revision")
    return {"intended_files": len(expected), "all_hashes_match": True, "extra_files": extras}


def verify_citations(source):
    macros = ET.parse(source / "macros.xml").getroot()
    tokens = {n.attrib["name"]: n.text or "" for n in macros.findall("token")}
    citation = macros.find("xml[@name='citations']/citations/citation")
    require(citation is not None and citation.attrib.get("type") == "bibtex", "Missing shared citation")
    text = citation.text or ""
    for required in ("Yu, Bohyeon and Diaz, Aaron", "10.5281/zenodo.22821665", "Software version 0.2.0"):
        require(required in text, "Published citation differs")
    result = {}
    for identifier in sorted(TOOL_IDS):
        tool = ET.parse(source / (identifier + ".xml")).getroot()
        version = tool.attrib["version"]
        profile = tool.attrib.get("profile", "")
        for token, value in tokens.items():
            version = version.replace(token, value)
            profile = profile.replace(token, value)
        require(version == VERSION and profile == "25.0", "XML version/profile differs")
        require(tool.find("macros/import").text == "macros.xml"
                and tool.find("expand[@macro='citations']") is not None, "Tool does not include citation")
        result[identifier] = text.strip()
    return result


def stage_workflow(destination, tools):
    source = ROOT / "galaxy/workflows"
    shutil.copytree(source, destination / "workflows")
    # Fixtures only. No local tool XML, macros, adapter or .shed.yml is staged.
    shutil.copytree(ROOT / "galaxy/tools/test-data", destination / "tools/test-data")
    path = destination / "workflows/spice_lineage_analysis.ga"
    original = json.loads(path.read_text())
    modified = copy.deepcopy(original)
    changed = []
    for step in modified["steps"].values():
        identifier = step.get("tool_id")
        if identifier in tools:
            step["tool_id"] = tools[identifier]
            step["tool_shed_repository"] = {"name": NAME, "owner": OWNER,
                                            "changeset_revision": REVISION, "tool_shed": HOST}
            changed.append(step["label"])
    require(len(changed) == 5, "Expected five SPICE workflow references")
    # Inverse transformation proves every parameter, connection and other step is unchanged.
    restored = copy.deepcopy(modified)
    inverse = {v: k for k, v in tools.items()}
    for step in restored["steps"].values():
        if step.get("tool_id") in inverse:
            step["tool_id"] = inverse[step["tool_id"]]
            del step["tool_shed_repository"]
    require(restored == original, "Workflow scientific content changed")
    save(path, modified)
    inventory = destination / "workflows/tools.yml"
    original_inventory = inventory.read_text()
    require(IQTREE_REVISION in original_inventory, "Missing pinned IUC IQ-TREE revision")
    inventory.write_text(original_inventory + f"- tool_shed: {HOST}\n  name: {NAME}\n  owner: {OWNER}\n"
                         f"  changeset_revision: {REVISION}\n  tool_shed_url: {SHED}\n"
                         f"  revisions:\n  - {REVISION}\n")
    save(destination / "workflow-identity-changes.json", {"changed_labels": changed,
         "parameters_and_connections_unchanged": True, "iqtree_revision": IQTREE_REVISION,
         "original_sha256": sha256(source / path.name), "published_copy_sha256": sha256(path)})
    return path


def verify_installed_tools(directory, tools, manifest):
    config = ET.parse(directory / "shed_tools_conf.xml").getroot()
    installed = [n for n in config.iter("tool") if n.attrib.get("guid") in tools.values()]
    require(len(installed) == 5, "Galaxy did not register five published SPICE GUIDs")
    records = []
    for node in installed:
        require(node.findtext("tool_shed") == HOST and node.findtext("repository_owner") == OWNER
                and node.findtext("repository_name") == NAME
                and node.findtext("installed_changeset_revision") == REVISION,
                "Galaxy installed a different Tool Shed revision")
        records.append({"guid": node.attrib["guid"], "file": node.attrib["file"],
                        "changeset": node.findtext("installed_changeset_revision")})
    candidates = list((directory / "shed_tools").rglob("spice_filter.xml"))
    require(len(candidates) == 1, "Ambiguous installed SPICE wrapper directory")
    payload = compare_payload(candidates[0].parent, manifest, strict=False)
    return {"tools": records, "payload": payload, "root": str(candidates[0].parent)}


def audit_jobs(path, tools, prefix, expected):
    tests = json.loads(path.read_text())["tests"]
    if expected == 6:
        jobs = [t["data"]["job"] for t in tests]
    else:
        steps = tests[0]["data"]["invocation_details"]["steps"].values()
        jobs = [j for step in steps for j in step.get("jobs", [])
                if j["tool_id"] in tools.values() or j["tool_id"].startswith("spice_")]
    require(len(jobs) == expected, "Unexpected published SPICE job count")
    executions = []
    for job in jobs:
        require(job["tool_id"] in tools.values() and job["state"] == "ok" and job["exit_code"] == 0,
                "Job did not use a successful published SPICE tool")
        markers = [line for line in job["stdout"].splitlines() if line.startswith("SPICE_GALAXY_EXECUTION ")]
        require(len(markers) == 1, "Missing/ambiguous installed-package execution marker")
        marker = json.loads(markers[0].split(" ", 1)[1])
        require(marker["prefix"] == str(prefix) and marker["spice_executable"] == str(prefix / "bin/spice")
                and marker["spice_import"].startswith(str(prefix / "lib/python"))
                and "/site-packages/spice_lineage/" in marker["spice_import"]
                and marker["version"] == "0.2.0", "Job escaped public package environment")
        executions.append({"job_id": job["id"], "tool_id": job["tool_id"], **marker})
    return executions


def audit_runtime_outputs(directory, binary, required_inference, evidence):
    evidence.mkdir()
    runtimes = []
    for path in directory.rglob("*"):
        if not path.is_file() or path.stat().st_size > 10000000:
            continue
        try:
            value = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        if not isinstance(value, dict) or "executables" not in value or "spice_version" not in value:
            continue
        require(value.get("success") is True and value["spice_version"] == "0.2.0", "Unsuccessful runtime output")
        bt = value["executables"].get("BayesTraits", {})
        require(bt.get("path") == str(binary) and bt.get("sha256") == BT_BINARY_SHA256,
                "Runtime did not resolve external verified BayesTraits")
        if value["command"] == "ancestry" or (value["command"] == "plasticity"
                and value["parameters"].get("perm_replicates", 0) > 0):
            require(bt.get("recorded_banner", "").startswith("BayesTraits V4.1.3"),
                    "Runtime lacks banner from actual BayesTraits inference")
            destination = evidence / f"{len(runtimes) + 1}-{value['command']}.runtime.json"
            save(destination, value)
            runtimes.append({"source_file": str(path), "retained_file": str(destination),
                             "command": value["command"], "bayestraits": bt})
    require(len(runtimes) == required_inference, "Missing inference runtime outputs")
    return runtimes


def check(args, work, report):
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "Linux x86_64 required")
    require(not work.is_relative_to(ROOT) and " " not in str(work), "Use a new external directory without spaces")
    require(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=work,
                           capture_output=True).returncode != 0, "Work directory must be outside Git")
    planemo = args.planemo.resolve()
    build = args.conda_prefix.resolve()
    home = work / "home"
    home.mkdir()
    env = {"PATH": f"{planemo.parent}:{build / 'bin'}:/usr/bin:/bin", "HOME": str(home),
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC", "PYTHONNOUSERSITE": "1",
           "PYTHONUNBUFFERED": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "CONDA_CHANNEL_PRIORITY": "strict", "CONDA_SOLVER": "libmamba", "CONDA_ANACONDA_UPLOAD": "false",
           "HGRCPATH": "", "HGPLAIN": "1", "PIP_BUILD_CONSTRAINT": str(ROOT / "ci/galaxy-build-constraints.txt")}
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    report["checkout_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    report["planemo"] = run([planemo, "--version"], work, env, "planemo-version", report, 60).strip()
    require(report["planemo"] == f"planemo, version {PLANEMO_VERSION}", "Unexpected Planemo version")
    tools = read_published_metadata(work, "published-before")
    report["published"] = {"server": SHED, "owner": OWNER, "name": NAME,
                           "repository_id": REPOSITORY_ID, "changeset": REVISION, "tools": tools}
    manifest = json.loads(MANIFEST.read_text())
    hg = planemo.parent / "hg"
    source = work / "published-source"
    run([hg, "clone", "--rev", REVISION, f"{SHED}/repos/{OWNER}/{NAME}", source],
        work, env, "published-clone", report, 300)
    revision = run([hg, "-R", source, "log", "-r", ".", "--template", "{node}"],
                   work, env, "published-revision", report, 60).strip()
    require(revision == manifest["full_changeset"], "Downloaded Mercurial node differs")
    report["published"]["full_changeset"] = revision
    report["published"]["archive_comparison"] = compare_payload(source, manifest)
    report["published"]["citations"] = verify_citations(source)
    report["published"]["reviewed_archive_sha256"] = ARCHIVE_SHA256
    save(work / "published-verification.json", report["published"])
    workflow = stage_workflow(work / "galaxy", tools)
    # Planemo 0.75.47 hardcodes MAIN_TOOLSHED_URL in _lint_tool_ids.
    # Replace only that inappropriate lint lookup with the strict metadata and
    # installed-revision checks above/below. No execution test is skipped.
    report["workflow_lint"] = {"excluded_linter": "tool_ids",
        "reason": "Planemo 0.75.47 queries Main Tool Shed for Test Tool Shed IDs",
        "replacement": "exact Test Tool Shed metadata, installed GUID and revision assertions"}
    run([planemo, "workflow_lint", "--fail_level", "error", "--skip", "tool_ids", workflow], work, env, "workflow-lint", report, 300)
    report["iqtree"] = verify_iqtree_revision()
    if args.metadata_only:
        report.update(status="incomplete", complete=False, pending=["published wrapper execution", "published workflow execution"])
        return

    report["public_conda"] = prepare_public_artifact(work / "public-artifact")
    require(report["public_conda"]["sha256"] == PUBLIC_SHA256, "Public SPICE artifact changed")
    cache = work / "conda-pkgs"
    cache.mkdir()
    conda = work / "public-conda"
    env.update(CONDA_PKGS_DIRS=str(cache), CONDA_ENVS_PATH=str(conda / "envs"))
    report["public_cache"] = {"path": str(cache), "initial_entries": list(cache.iterdir())}
    run([build / "bin/conda", "create", "--yes", "--prefix", conda, "--override-channels",
         "--strict-channel-priority", "-c", "conda-forge", "-c", "bioconda", "conda=26.7.2", "python=3.11"],
        work, env, "public-conda-bootstrap", report)
    require(not list(cache.glob("spice-lineage*")) and not list((conda / "envs").glob("*spice*")),
            "SPICE was cached before Galaxy installation")
    env["PATH"] = f"{planemo.parent}:{conda / 'bin'}:/usr/bin:/bin"
    galaxy = work / "galaxy-source"
    for label, command in [
        ("galaxy-init", ["git", "init", galaxy]),
        ("galaxy-origin", ["git", "-C", galaxy, "remote", "add", "origin", "https://github.com/galaxyproject/galaxy.git"]),
        ("galaxy-fetch", ["git", "-C", galaxy, "fetch", "--depth=1", "origin", GALAXY_COMMIT]),
        ("galaxy-checkout", ["git", "-C", galaxy, "checkout", "--detach", "FETCH_HEAD"]),
    ]:
        run(command, work, env, label, report, 600)
    observed = run(["git", "-C", galaxy, "rev-parse", "HEAD"], work, env, "galaxy-revision", report, 60).strip()
    require(observed == GALAXY_COMMIT, "Pinned Galaxy source differs")
    run(["git", "-C", galaxy, "diff", "--exit-code", "HEAD"], work, env, "galaxy-clean", report, 60)
    report["galaxy"] = {"commit": observed, "profile": "25.0", "server_python": "3.11"}
    venv = work / "galaxy-venv"
    run([planemo.parent / "python", "-m", "venv", venv], work, env, "galaxy-venv", report, 180)
    run([venv / "bin/python", "-m", "pip", "install", "pip==26.2.1"], work, env, "galaxy-pip", report, 300)
    env["GALAXY_VIRTUAL_ENV"] = str(venv)
    binary = None
    try:
        with tempfile.TemporaryDirectory(prefix="spice-published-bayestraits-") as temporary:
            binary, info = bayestraits(Path(temporary), env)
            require(info["sha256"] == BT_BINARY_SHA256 and info["archive_sha256"] == BT_ARCHIVE_SHA256,
                    "Unexpected external BayesTraits download")
            report["bayestraits"] = info
            job_config = work / "job-conf.yml"
            save(job_config, {"runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
                 "execution": {"default": "local", "environments": {"local": {"runner": "local", "tmp_dir": True,
                    "env": [{"name": "BAYESTRAITS_BIN", "value": str(binary)},
                            {"name": "OPENBLAS_NUM_THREADS", "value": "1"},
                            {"name": "OMP_NUM_THREADS", "value": "1"}]}}},
                 "tools": [{"class": "local", "environment": "local"}]})
            common = ["--galaxy_root", galaxy, "--galaxy_python_version", "3.11", "--galaxy_startup_timeout", "1200",
                      "--conda_prefix", conda, "--conda_channels", "conda-forge,bioconda", "--conda_dependency_resolution",
                      "--conda_auto_install", "--no_conda_auto_init", "--job_workers", "1", "--no_cleanup",
                      "--job_config_file", job_config]
            # This empty selector directory contains no local wrapper or test-data substitute.
            selector = work / "shed-selector"
            selector.mkdir()
            commands = [
                ("tools", [planemo, "shed_test", selector, "--shed_target", SHED, "--owner", OWNER, "--name", NAME], 6, 6, 2),
                ("workflow", [planemo, "test", workflow], 1, 9, 6),
            ]
            for label, command, cases, jobs, inference in commands:
                read_published_metadata(work, label + "-revision-guard")
                shed = work / (label + "-shed")
                datasets = work / (label + "-datasets")
                datasets.mkdir()
                report_path = work / (label + ".json")
                run([*command, *common, "--shed_data_dir", shed,
                     "--database_connection", "sqlite:///" + str(work / (label + ".sqlite")),
                     "--file_path", datasets, "--test_output", work / (label + ".html"),
                     "--test_output_json", report_path, "--test_output_xunit", work / (label + ".xml")],
                    work, env, label, report)
                report[label] = validate_test_report(report_path, cases)
                installed = verify_installed_tools(shed, tools, manifest)
                save(work / (label + "-installed-revision.json"), installed)
                report.setdefault("installed_revisions", {})[label] = installed
                prefix = conda / "envs/__spice-lineage@0.2.0"
                report.setdefault("public_installs", {})[label] = verify_public_install(
                    prefix, report["public_conda"], work / (label + "-public-install"))
                require(sha256(cache / report["public_conda"]["filename"]) == PUBLIC_SHA256,
                        "Galaxy's downloaded package checksum differs")
                executions = audit_jobs(report_path, tools, prefix, jobs)
                save(work / (label + "-job-provenance.json"), executions)
                runtimes = audit_runtime_outputs(datasets, binary, inference, work / (label + "-runtime-evidence"))
                save(work / (label + "-bayestraits-execution.json"), runtimes)
                if label == "workflow":
                    report["workflow_execution"] = validate_workflow_execution(report_path)
                report[label].update(public_jobs=len(executions), external_bayestraits_inference_jobs=len(runtimes))
    finally:
        if binary is not None:
            report["bayestraits_removed"] = not binary.exists()
            require(report["bayestraits_removed"], "Temporary BayesTraits executable remains")
    require(read_published_metadata(work, "published-after") == tools, "Published metadata changed during execution")
    report.update(status="pass", complete=True, skipped=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--planemo", type=Path, required=True)
    parser.add_argument("--conda-prefix", type=Path, default=Path(sys.prefix))
    parser.add_argument("--metadata-only", action="store_true", help="Explicitly incomplete; no execution claim")
    args = parser.parse_args()
    work = args.work_dir.expanduser().resolve()
    require(not work.is_relative_to(ROOT), "Evidence directory must be outside repository")
    work.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "complete": False, "tool_shed_writes": False, "commands": []}
    started = time.monotonic()
    try:
        check(args, work, report)
    except Exception as exc:
        report.update(status="failed", complete=False, error=str(exc))
        raise
    finally:
        report["seconds"] = round(time.monotonic() - started, 2)
        save(work / "result.json", report)
    print(json.dumps({"status": report["status"], "complete": report["complete"], "evidence": str(work)}))


if __name__ == "__main__":
    main()
