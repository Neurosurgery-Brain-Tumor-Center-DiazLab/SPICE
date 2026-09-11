#!/usr/bin/env python3
"""Real Linux integration through a fresh non-editable wheel; never skip tools."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]
BT_URL = "https://www.evolution.reading.ac.uk/BayesTraitsV4.1.3/Files/BayesTraitsV4.1.3-Linux.tar.gz"
BT_ARCHIVE_SHA256 = "cf0f5d9afa6ab74ae5aa6f386d1b3a4bc20d25643878aecddab459259b030674"
BT_MEMBER = "BayesTraitsV4.1.3-Linux/BayesTraitsV4"
BT_BINARY_SHA256 = "711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d"
R_PACKAGES = ("ape", "coda", "janitor", "posterior", "dplyr", "progress",
              "phangorn", "phytools", "ggplot2", "ggtree", "ggsci")
PY_PACKAGES = ("pandas", "numpy", "python-dateutil", "pytz", "six", "tzdata")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd, work, env, name, timeout=600, input=None):
    log = work / (name + ".log")
    print("+ " + " ".join(map(str, cmd)), flush=True)
    with log.open("w") as f:
        result = subprocess.run(list(map(str, cmd)), cwd=work, env=env,
                                input=input, text=True, stdout=f,
                                stderr=subprocess.STDOUT, timeout=timeout)
    output = log.read_text(errors="replace")
    if result.returncode:
        print(output[-16000:], flush=True)
        raise RuntimeError(f"{name} failed ({result.returncode}); full log: {log}")
    return output


def executable(candidate, label):
    found = shutil.which(candidate) if candidate else None
    if not found:
        raise RuntimeError(f"{label} executable missing or not executable: {candidate!r}")
    path = Path(found).resolve()
    # The real suite targets Linux binaries, never shell fixtures or substitutes.
    with path.open("rb") as f:
        if f.read(4) != b"\x7fELF":
            raise RuntimeError(f"{label} must be a real Linux ELF executable: {path}")
    return path


def bayestraits(tools_dir, env):
    supplied = env.get("BAYESTRAITS_BIN")
    if supplied:
        binary = executable(supplied, "BAYESTRAITS_BIN")
        source = "explicitly supplied BAYESTRAITS_BIN"
    else:
        archive = tools_dir / "BayesTraitsV4.1.3-Linux.tar.gz"
        print("Downloading official BayesTraits: " + BT_URL, flush=True)
        with urllib.request.urlopen(BT_URL, timeout=120) as response, archive.open("wb") as f:
            if not response.url.startswith("https://www.evolution.reading.ac.uk/"):
                raise RuntimeError("Unexpected BayesTraits download origin")
            shutil.copyfileobj(response, f)
        if sha256(archive) != BT_ARCHIVE_SHA256:
            raise RuntimeError("BayesTraits archive SHA-256 mismatch; refusing execution")
        binary = tools_dir / "BayesTraitsV4"
        with tarfile.open(archive) as tar:
            member = tar.getmember(BT_MEMBER)
            if not member.isfile():
                raise RuntimeError("BayesTraits archive member is not a regular file")
            with tar.extractfile(member) as src, binary.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        if sha256(binary) != BT_BINARY_SHA256:
            raise RuntimeError("BayesTraits binary SHA-256 mismatch; refusing execution")
        binary.chmod(0o700)
        source = BT_URL
    # This interactive executable needs a newline to leave its usage banner.
    probe = subprocess.run([str(binary)], input="\n", text=True, capture_output=True,
                           timeout=20, cwd=tools_dir, env=env)
    output = probe.stdout + probe.stderr
    if probe.returncode or not re.search(r"^BayesTraits V4\.1\.3(?:\s|$)", output, re.M):
        raise RuntimeError(f"BayesTraits V4.1.3 required; probe returned {probe.returncode}: {output}")
    # V4.1.3 has no --version API; a successful usage banner identifies it.
    print(f"BayesTraits usage/version probe exit: {probe.returncode}", flush=True)
    return binary, {"path": str(binary), "sha256": sha256(binary),
                    "usage_probe_exit": probe.returncode,
                    "banner": output.splitlines()[0], "source": source,
                    "archive_sha256": BT_ARCHIVE_SHA256 if not supplied else None}


def check(work, repeats):
    started = time.monotonic()
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONOPTIMIZE") and not k.startswith("GIT_")}
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    # Bound test resources and avoid old static OpenBLAS thread teardown on WSL1.
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if platform.system() != "Linux" or platform.machine() != "x86_64" or sys.version_info < (3, 10):
        raise RuntimeError("Integration requires Linux x86_64 and Python >= 3.10")
    if subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=work, env=env,
                      capture_output=True).returncode == 0:
        raise RuntimeError("Integration work directory must be outside Git")
    iq = executable(env.get("IQTREE2_BIN") or shutil.which("iqtree2") or shutil.which("iqtree"), "IQ-TREE")
    iq_version = run([iq, "--version"], work, env, "iqtree-version")
    if not re.search(r"IQ-TREE.*version 2\.4\.0\b", iq_version):
        raise RuntimeError(f"IQ-TREE 2.4.0 required; found: {iq_version}")
    env["IQTREE2_BIN"] = str(iq)
    if not shutil.which("Rscript"):
        raise RuntimeError("Rscript is required; no skips")
    code = ('p <- c(' + ",".join(json.dumps(x) for x in R_PACKAGES) + '); '
            'stopifnot(all(vapply(p,requireNamespace,logical(1),quietly=TRUE))); '
            'cat(R.version.string,"\\n"); print(sapply(p, function(x) as.character(packageVersion(x))))')
    print(run(["Rscript", "--vanilla", "-e", code], work, env, "r-versions"), flush=True)
    print(f"Python: {sys.version}; IQ-TREE: {iq}\n{iq_version}", flush=True)
    print(run([sys.executable, "-m", "build", "--wheel", "--outdir", work / "dist", ROOT],
              work, env, "build"), flush=True)
    wheels = list((work / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one newly built wheel")
    prefix = work / "venv"
    venv.EnvBuilder(with_pip=True).create(prefix)
    python = prefix / "bin/python"
    constraints = work / "python-constraints.txt"
    constraints.write_text("".join(f"{p}=={importlib.metadata.version(p)}\n" for p in PY_PACKAGES))
    run([python, "-m", "pip", "install", "--constraint", constraints, wheels[0]], work, env, "install")
    run([python, "-m", "pip", "check"], work, env, "pip-check")
    env["PATH"] = str(prefix / "bin") + os.pathsep + env["PATH"]
    neutral = work / "external tests with spaces"
    shutil.copytree(ROOT / "tests/integration", neutral)
    source_hashes = {p.relative_to(ROOT).as_posix(): sha256(p)
                     for p in (ROOT / "spice_lineage").rglob("*")
                     if p.is_file() and (p.suffix in (".py", ".R") or p.name == "VERSION")}
    # Downloaded binaries live separately from retained logs/results, and are always deleted.
    with tempfile.TemporaryDirectory(prefix="spice-bayestraits-") as temp:
        bt, bt_info = bayestraits(Path(temp), env)
        env["BAYESTRAITS_BIN"] = str(bt)
        print(json.dumps(bt_info, indent=2), flush=True)
        expected = {"version": (ROOT / "VERSION").read_text().strip(),
                    "source_root": str(ROOT), "source_sha256": source_hashes,
                    "wheel": str(wheels[0]), "wheel_sha256": sha256(wheels[0]),
                    "IQ-TREE": {"path": str(iq), "sha256": sha256(iq)},
                    "BayesTraits": bt_info, "repeats": repeats}
        (neutral / "expected.json").write_text(json.dumps(expected, indent=2))
        run([python, neutral / "checks.py"], work, env, "integration", timeout=3600)
    elapsed = round(time.monotonic() - started, 2)
    report = json.loads((neutral / "results.json").read_text())
    report.update(total_seconds=elapsed, wheel=str(wheels[0]), wheel_sha256=sha256(wheels[0]))
    (work / "result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    print(f"PASS: full real integration, zero skips; evidence: {work}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, help="New external directory; logs and results are retained")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat both real-tool fixtures (default 1)")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    work = args.work_dir.resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="spice-integration-"))
    if work.is_relative_to(ROOT):
        parser.error("--work-dir must be outside the source checkout")
    if args.work_dir:
        work.mkdir(parents=True, exist_ok=False)
    print(f"Integration evidence: {work}", flush=True)
    try:
        check(work, args.repeat)
    except Exception as exc:
        print(f"FAIL: {exc}\nRetained logs and outputs: {work}", file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
