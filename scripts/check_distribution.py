#!/usr/bin/env python3
"""Build/test a local Conda package and OCI image; never publish or skip checks.

Default: complete Conda + Docker validation. --conda-only explicitly produces
partial evidence on hosts without Docker; it is NOT a complete distribution pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "packaging/bioconda/spice-lineage"
CONTAINERFILE = ROOT / "packaging/container/Containerfile"
SOURCE_REVISION = "e6c23ca39f44a47a8351e49d642e977ad8a7f87b"
SUBCOMMANDS = ["import-monopogen", "filter", "phylogeny", "clones",
               "ancestry", "plasticity", "summarize"]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(command, work, env, name, timeout=3600):
    command = list(map(str, command))
    print("+ " + " ".join(command), flush=True)
    log = work / (name + ".log")
    with log.open("w") as f:
        proc = subprocess.run(command, cwd=work, env=env, text=True, stdout=f,
                              stderr=subprocess.STDOUT, timeout=timeout)
    text = log.read_text(errors="replace")
    if proc.returncode:
        print(text[-18000:], flush=True)
        raise RuntimeError(f"{name} failed ({proc.returncode}); full log: {log}")
    return text


def clean_environment(work):
    # Do not inherit source imports, executable overrides, R libraries or Git auth.
    # Conda may reuse verified downloads; channel and installed prefix are always new.
    home = work / "home"
    home.mkdir()
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TZ": "UTC",
            "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
            "CONDA_CHANNEL_PRIORITY": "strict", "CONDA_SOLVER": "libmamba",
            "CONDA_SUBDIR": "linux-64", "CONDA_BLD_PATH": str(work / "build"),
            "CONDA_ANACONDA_UPLOAD": "false"}


def inspect_package(package, work, expected):
    from conda_package_handling.api import extract
    unpacked = work / "artifact inspection"
    extract(str(package), dest_dir=str(unpacked))
    index = json.loads((unpacked / "info/index.json").read_text())
    require(index["name"] == "spice-lineage" and index["version"] == expected["version"]
            and index["build_number"] == 0 and index["subdir"] == "noarch", "Package metadata")
    link = json.loads((unpacked / "info/link.json").read_text())
    require(link["noarch"]["type"] == "python" and
            link["noarch"]["entry_points"] == ["spice = spice_lineage.cli:main"],
            "Missing noarch console entry point")
    payload = (unpacked / "info/files").read_text().splitlines()
    require(payload, "Empty Conda artifact")
    info_prefix = "site-packages/spice_lineage-" + expected["version"] + ".dist-info/"
    for name in payload:
        require(name.startswith("site-packages/spice_lineage/") or name.startswith(info_prefix),
                f"Unexpected Conda payload file: {name}")
        require(not any(p in (".git", ".local-ci", "__pycache__") for p in Path(name).parts)
                and not name.endswith(".pyc"), f"Build junk in Conda package: {name}")
    actual = {"spice_lineage/" + p.relative_to(unpacked / "site-packages/spice_lineage").as_posix():
              sha256(p) for p in (unpacked / "site-packages/spice_lineage").rglob("*") if p.is_file()}
    require(actual == expected["source_sha256"], "Conda Python/R payload differs from source")
    require((unpacked / info_prefix / "licenses/LICENSE").is_file(), "License missing")
    # The exact payload allowlist/hashes excludes external binaries and source-tree junk.
    (work / "package-files.json").write_text(json.dumps(payload, indent=2) + "\n")
    return index


def prepare_checks(work):
    inputs = work / "inputs with spaces"
    inputs.mkdir()
    checks = work / "checks"
    checks.mkdir()
    for source, destination in [
        (ROOT / "examples/standard", inputs / "standard"),
        (ROOT / "tests/integration/fixtures/phylogeny/standard", inputs / "phylogeny"),
        (ROOT / "tests/integration/fixtures/ancestry", inputs / "ancestry"),
    ]:
        shutil.copytree(source, destination)
    shutil.copyfile(ROOT / "tests/distribution/supported tree.nwk", inputs / "supported tree.nwk")
    for source in (ROOT / "tests/distribution/checks.py", ROOT / "tests/standard_example.py",
                   ROOT / "tests/integration/verify_trees.R",
                   ROOT / "tests/integration/verify_clone_equivalence.R"):
        shutil.copyfile(source, checks / source.name)
    package = ROOT / "spice_lineage"
    expected = {"version": (ROOT / "VERSION").read_text().strip(), "source_root": str(ROOT),
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p)
                                  for p in package.rglob("*") if p.is_file() and
                                  (p.suffix in (".py", ".R") or p.name == "VERSION")},
                "r_files": sorted(p.name for p in (package / "resources/r").glob("*.R")),
                "subcommands": SUBCOMMANDS}
    (inputs / "expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    return inputs, checks, expected


def make_container_context(work, package, records):
    context = work / "container-context"
    channel = context / "channel/noarch"
    channel.mkdir(parents=True)
    shutil.copyfile(package, channel / package.name)
    shutil.copyfile(CONTAINERFILE, context / "Containerfile")
    lock = ["@EXPLICIT"]
    local_count = 0
    for record in sorted(records, key=lambda r: r["name"]):
        digest = record.get("sha256")
        require(digest and re.fullmatch(r"[0-9a-f]{64}", digest), "Missing package SHA-256")
        if record["name"] == "spice-lineage":
            require(digest == sha256(package), "Installed SPICE artifact hash mismatch")
            url = "file:///tmp/channel/noarch/" + package.name
            local_count += 1
        else:
            url = record["url"]
            require(url.startswith(("https://conda.anaconda.org/conda-forge/",
                                    "https://conda.anaconda.org/bioconda/")),
                    f"Unexpected runtime source: {url}")
        lock.append(url + "#" + digest)
    require(local_count == 1, "Container lock must install exactly one local SPICE package")
    (context / "runtime-linux-64.lock").write_text("\n".join(lock) + "\n")
    return context


def check_container(work, env, image, package, context, inputs, checks, expected):
    base = re.search(r"^ARG BASE_IMAGE=(.+)$", CONTAINERFILE.read_text(), re.M).group(1)
    require("@sha256:" in base and ":latest" not in base, "Base image must be digest pinned")
    run(["docker", "info"], work, env, "docker-info", 60)
    run(["docker", "build", "--platform", "linux/amd64", "--file", context / "Containerfile",
         "--build-arg", "SPICE_VERSION=" + expected["version"],
         "--build-arg", "SOURCE_REVISION=" + SOURCE_REVISION,
         "--build-arg", "PACKAGE_SHA256=" + sha256(package),
         "--tag", image, context], work, env, "container-build")
    info = json.loads(run(["docker", "image", "inspect", image], work, env, "image-inspect", 60))[0]
    require(info["Architecture"] == "amd64" and info["Os"] == "linux", "Image platform")
    require(not info["Config"].get("Entrypoint"), "Image must support arbitrary workflow commands")
    labels = info["Config"]["Labels"]
    for name, value in {"title": "SPICE", "version": expected["version"],
                        "source": "https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE",
                        "licenses": "GPL-3.0-only", "revision": SOURCE_REVISION}.items():
        require(labels["org.opencontainers.image." + name] == value, f"Wrong OCI label: {name}")
    mounted = work / "container outputs with spaces"
    mounted.mkdir()
    invocation = ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none",
                  "--read-only", "--tmpfs", "/tmp:rw,exec,nosuid,size=512m",
                  "--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/tmp",
                  "--env", "OPENBLAS_NUM_THREADS=1", "--env", "OMP_NUM_THREADS=1",
                  "--env", "PYTHONDONTWRITEBYTECODE=1",
                  "--mount", f"type=bind,src={inputs},dst=/input data,readonly",
                  "--mount", f"type=bind,src={checks},dst=/checks,readonly",
                  "--mount", f"type=bind,src={mounted},dst=/output data",
                  "--workdir", "/output data"]
    probe = ("from pathlib import Path; import os; "
             "assert not os.access('/input data/supported tree.nwk', os.W_OK); "
             "assert not Path('/tmp/channel').exists(); "
             "assert not Path('/tmp/runtime-linux-64.lock').exists(); "
             "assert not list(Path('/opt/conda/pkgs').glob('*.conda')); "
             "assert not list(Path('/opt/conda/pkgs').glob('*.tar.bz2')); "
             "assert not Path('/.git').exists()")
    run([*invocation, image, "python", "-c", probe], work, env, "container-layout")
    run([*invocation, image, "python", "/checks/checks.py", "--inputs", "/input data",
         "--output", "/output data/results with spaces", "--prefix", "/opt/conda"],
        work, env, "container-checks")
    result = json.loads((mounted / "results with spaces/result.json").read_text())
    require(result["status"] == "pass" and result["skipped"] == 0, "Container tests incomplete")
    outputs = [p for p in mounted.rglob("*") if p.is_file()]
    require(outputs and all(p.stat().st_uid == os.getuid() and os.access(p, os.R_OK) for p in outputs),
            "Container outputs not owned/readable by invoking host user")
    result.update(base_image=base, image_id=info["Id"], repo_digests=info.get("RepoDigests", []),
                  host_output_uid=os.getuid(), image_tag=image)
    return result


def check(work, conda_only, image):
    require(platform.system() == "Linux" and platform.machine() == "x86_64",
            "Distribution checks require Linux x86_64")
    conda = shutil.which("conda")
    require(conda, "Activate the locked distribution toolchain; conda is required")
    env = clean_environment(work)
    require(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=work, env=env,
                           capture_output=True).returncode != 0, "Work directory is inside Git")
    inputs, checks, expected = prepare_checks(work)
    input_hashes = {str(p): sha256(p) for p in inputs.rglob("*") if p.is_file()}
    channel = work / "channel"
    channel.mkdir()
    common = ["--override-channels", "-c", "conda-forge", "-c", "bioconda"]
    run([conda, "list", "--explicit", "--sha256"], work, env, "toolchain-packages")
    run([conda, "render", RECIPE, "--python", "3.11", *common], work, env, "recipe-render")
    run([conda, "build", RECIPE, "--python", "3.11", *common, "--no-anaconda-upload",
         "--output-folder", channel], work, env, "recipe-build")
    packages = list((channel / "noarch").glob("spice-lineage-*.conda"))
    packages += list((channel / "noarch").glob("spice-lineage-*.tar.bz2"))
    require(len(packages) == 1, "Expected exactly one freshly built Conda package")
    package = packages[0]
    index = inspect_package(package, work, expected)
    (channel / "linux-64").mkdir(exist_ok=True)
    run([conda, "index", channel], work, env, "channel-index")
    prefix = work / "runtime-env"
    run([conda, "create", "--yes", "--prefix", prefix, "--strict-channel-priority",
         "--override-channels", "-c", channel.as_uri(), "-c", "conda-forge", "-c", "bioconda",
         "spice-lineage=" + expected["version"], "python=3.11"], work, env, "clean-install")
    records = [json.loads(p.read_text()) for p in (prefix / "conda-meta").glob("*.json")]
    installed = [r for r in records if r["name"] == "spice-lineage"]
    require(len(installed) == 1 and
            Path(unquote(urlparse(installed[0]["url"]).path)).resolve() == package.resolve(),
            "Installed SPICE did not come from the newly built local package")
    package_list = run([conda, "list", "--prefix", prefix, "--explicit", "--sha256"],
                       work, env, "runtime-packages")
    print(package_list, flush=True)
    runtime_env = {k: v for k, v in env.items() if not k.startswith("CONDA_")}
    runtime_env["PATH"] = str(prefix / "bin") + ":/usr/bin:/bin"
    output = work / "conda outputs with spaces"
    run([prefix / "bin/python", checks / "checks.py", "--inputs", inputs,
         "--output", output, "--prefix", prefix], work, runtime_env, "conda-checks")
    conda_result = json.loads((output / "result.json").read_text())
    require(conda_result["status"] == "pass" and conda_result["skipped"] == 0,
            "Conda-installed checks incomplete")
    context = make_container_context(work, package, records)
    report = {"status": "conda-pass-container-pending", "complete": False,
              "source_commit": SOURCE_REVISION,
              "checkout_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                                        text=True).strip(),
              "spice_version": expected["version"], "recipe": str(RECIPE.relative_to(ROOT)),
              "recipe_sha256": sha256(RECIPE / "meta.yaml"), "package_metadata": index,
              "package": str(package), "package_filename": package.name,
              "package_sha256": sha256(package), "clean_prefix": str(prefix),
              "conda_checks": conda_result, "container": {"status": "pending"},
              "runtime_packages": [{"name": r["name"], "version": r["version"],
                                    "build": r["build"], "url": r["url"], "sha256": r["sha256"]}
                                   for r in sorted(records, key=lambda r: r["name"])],
              "published": False}
    report_path = work / "result.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if not conda_only:
        require(shutil.which("docker"), "Docker is required for complete validation; no silent skips")
        report["container"] = check_container(work, env, image, package, context, inputs, checks, expected)
        report.update(status="pass", complete=True)
    require(input_hashes == {str(p): sha256(p) for p in inputs.rglob("*") if p.is_file()},
            "Validation modified source fixtures")
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Package: {package.name}\nSHA-256: {sha256(package)}\nEvidence: {report_path}", flush=True)
    if conda_only:
        print("PARTIAL: Conda checks passed. Container checks remain REQUIRED on a Docker host.", flush=True)
    else:
        print("PASS: complete Conda + OCI distribution validation; zero skips; nothing published", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, help="New directory outside the checkout; retained")
    parser.add_argument("--conda-only", action="store_true",
                        help="Explicit partial validation; container acceptance remains pending")
    parser.add_argument("--image", default="spice-lineage:phase5-local", help="Local image tag; never pushed")
    args = parser.parse_args()
    work = args.work_dir.resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="spice-distribution-"))
    require(not work.is_relative_to(ROOT), "Work directory must be outside the checkout")
    require(" " not in str(work), "Conda-build prefixes need a work path without spaces; test paths contain spaces")
    if args.work_dir:
        work.mkdir(parents=True, exist_ok=False)
    print(f"Distribution evidence: {work}", flush=True)
    check(work, args.conda_only, args.image)


if __name__ == "__main__":
    main()
