#!/usr/bin/env python3
"""Public Bioconda identity checks shared by release and Galaxy validation.

This module never builds, uploads, or installs a package. Artifact and source
archives are downloaded independently of Conda's cache for identity checks.
"""
import bz2
import json
from pathlib import Path
import re
import shutil
import tarfile
import urllib.request

from check_distribution import inspect_package, sha256

VERSION = "0.2.0"
SOURCE_COMMIT = "5ebc4aec5df7df6c2e9cdb60c1259a2898e3e19f"
SOURCE_URL = ("https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/"
              "archive/refs/tags/v0.2.0.tar.gz")
SOURCE_SHA256 = "48d67b1e5300203d5ce953f2bea25b958772d1887ed8ad1b83f31ce6ced71236"
CHANNEL = "https://conda.anaconda.org/bioconda/noarch/"
CHANNELS = ("https://conda.anaconda.org/conda-forge/", "https://conda.anaconda.org/bioconda/")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def download(url, path):
    with urllib.request.urlopen(url, timeout=180) as response, path.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def validate_record(record, artifact):
    for key, value in {"name": "spice-lineage", "version": VERSION,
                       "build": artifact["build"], "build_number": 0, "subdir": "noarch",
                       "url": artifact["url"], "sha256": artifact["sha256"]}.items():
        require(record.get(key) == value, f"Public SPICE {key} mismatch: {record.get(key)!r}")
    require(record["url"] == CHANNEL + artifact["filename"], "SPICE origin is not public Bioconda")
    require(re.fullmatch(r"[0-9a-f]{64}", record["sha256"]), "Missing artifact SHA-256")


def prepare_public_artifact(work):
    work.mkdir(exist_ok=False)
    api_url = "https://api.anaconda.org/package/bioconda/spice-lineage"
    api_path = work / "anaconda.json"
    download(api_url, api_path)
    candidates = [f for f in json.loads(api_path.read_text())["files"]
                  if f.get("version") == VERSION and f["attrs"].get("subdir") == "noarch"
                  and f["attrs"].get("build_number") == 0 and "main" in f.get("labels", [])]
    require(len(candidates) == 1, "Public build 0 is absent or ambiguous")
    entry = candidates[0]
    filename = entry["basename"].removeprefix("noarch/")
    require(Path(filename).name == filename and filename.endswith((".conda", ".tar.bz2")),
            "Unexpected public artifact filename")
    repodata_path = work / "repodata.json.bz2"
    download(CHANNEL + "repodata.json.bz2", repodata_path)
    repodata = json.loads(bz2.decompress(repodata_path.read_bytes()))
    record = {**repodata.get("packages", {}), **repodata.get("packages.conda", {})}.get(filename)
    require(record is not None, "Artifact is absent from the official Bioconda index")
    require(record["sha256"] == entry["sha256"], "API/index SHA-256 disagreement")
    artifact = {"filename": filename, "url": CHANNEL + filename, "sha256": record["sha256"],
                "build": record["build"], "version": VERSION, "build_number": 0, "subdir": "noarch",
                "api_url": api_url, "upload_time": entry.get("upload_time"),
                "repodata_url": CHANNEL + "repodata.json.bz2",
                "repodata_sha256": sha256(repodata_path), "repodata_record": record}
    validate_record({**record, "url": artifact["url"]}, artifact)
    package = work / filename
    download(artifact["url"], package)
    require(sha256(package) == artifact["sha256"], "Downloaded public artifact checksum mismatch")
    source_archive = work / "v0.2.0.tar.gz"
    download(SOURCE_URL, source_archive)
    require(sha256(source_archive) == SOURCE_SHA256, "Immutable release archive checksum mismatch")
    source = work / "release"
    source.mkdir()
    with tarfile.open(source_archive) as archive:
        archive.extractall(source, filter="data")
    roots = list(source.iterdir())
    require(len(roots) == 1 and (roots[0] / "VERSION").read_text().strip() == VERSION,
            "Unexpected release archive layout/version")
    root = roots[0]
    expected = {"version": VERSION, "source_root": str(root),
                "source_sha256": {p.relative_to(root).as_posix(): sha256(p)
                                  for p in (root / "spice_lineage").rglob("*") if p.is_file()
                                  and (p.suffix in (".py", ".R") or p.name == "VERSION")}}
    inspection = work / "inspection"
    inspection.mkdir()
    inspect_package(package, inspection, expected)
    artifact.update(package=str(package), source_commit=SOURCE_COMMIT, source_url=SOURCE_URL,
                    source_archive_sha256=SOURCE_SHA256, release_root=str(root),
                    payload_matches_release=True, source_sha256=expected["source_sha256"])
    (work / "artifact.json").write_text(json.dumps(artifact, indent=2) + "\n")
    return artifact


def verify_public_install(prefix, artifact, evidence):
    records = [json.loads(p.read_text()) for p in (prefix / "conda-meta").glob("*.json")]
    spice = [r for r in records if r["name"] == "spice-lineage"]
    require(len(spice) == 1, "Galaxy SPICE installation record is missing or ambiguous")
    validate_record(spice[0], artifact)
    for record in records:
        require(record.get("url", "").startswith(CHANNELS),
                f"Non-public dependency origin: {record.get('name')}: {record.get('url')}")
    by_name = {r["name"]: r for r in records}
    require(by_name.get("iqtree", {}).get("version") == "2.4.0", "IQ-TREE 2.4.0 contract changed")
    require(by_name.get("r-base", {}).get("version") == "4.3.3", "Validated R 4.3.3 contract changed")
    packages = list(prefix.glob("lib/python*/site-packages/spice_lineage"))
    require(len(packages) == 1, "Missing or ambiguous installed SPICE payload")
    payload = {"spice_lineage/" + p.relative_to(packages[0]).as_posix(): sha256(p)
               for p in packages[0].rglob("*") if p.is_file()
               and (p.suffix in (".py", ".R") or p.name == "VERSION")}
    require(payload == artifact["source_sha256"], "Installed Python/R payload differs from release")
    evidence.mkdir(exist_ok=False)
    (evidence / "spice-conda-meta.json").write_text(json.dumps(spice[0], indent=2) + "\n")
    (evidence / "all-conda-meta.json").write_text(json.dumps(records, indent=2) + "\n")
    return {"prefix": str(prefix), "url": spice[0]["url"], "sha256": spice[0]["sha256"],
            "build": spice[0]["build"], "payload_matches_release": True,
            "iqtree": by_name["iqtree"]["version"], "r_base": by_name["r-base"]["version"],
            "package_count": len(records), "evidence": str(evidence)}
