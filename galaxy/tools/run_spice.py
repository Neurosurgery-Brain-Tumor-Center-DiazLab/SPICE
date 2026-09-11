"""Galaxy file/argument adapter. All analysis is delegated to installed spice."""
import csv
import json
import os
from pathlib import Path
import shutil
import sys


def write_manifest(elements, destination):
    """Preserve collection identifiers literally; never interpret them as shell text."""
    rows = []
    identifiers = set()
    for identifier, path in elements:
        if (not isinstance(identifier, str) or not identifier
                or identifier != identifier.strip()
                or any(c in identifier for c in "\t\r\n\x00")):
            raise ValueError("Clone identifiers must be nonempty, without boundary whitespace or control characters")
        if identifier in identifiers:
            raise ValueError("Duplicate clone collection identifier: " + identifier)
        identifiers.add(identifier)
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("Plasticity collection elements must be files")
        rows.append((identifier, str(resolved)))
    if not rows:
        raise ValueError("The plasticity collection is empty")
    with Path(destination).open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["clone_id", "plasticity_test"])
        writer.writerows(rows)


def main():
    with open(sys.argv[1], encoding="utf-8") as handle:
        specification = json.load(handle)
    argv = specification["argv"]
    if (not isinstance(argv, list) or not argv
            or argv[0] not in {"filter", "clones", "ancestry", "plasticity", "summarize"}
            or not all(isinstance(arg, str) and "\x00" not in arg for arg in argv)):
        raise ValueError("Invalid SPICE argument vector")
    import spice_lineage
    prefix = Path(sys.prefix).resolve()
    package = Path(spice_lineage.__file__).resolve()
    executable = Path(shutil.which("spice") or "missing-spice").resolve()
    if (not package.is_relative_to(prefix) or "site-packages" not in package.parts
            or executable != prefix / "bin/spice"):
        raise RuntimeError("Galaxy requires spice and its import from the resolved package environment")
    for source, name in specification.get("stage", []):
        destination = Path(name)
        if destination.is_absolute() or ".." in destination.parts:
            raise ValueError("Staging destinations must be relative to the job directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(Path(source).resolve(strict=True))
    Path("out").mkdir(exist_ok=False)
    if "collection" in specification:
        write_manifest(specification["collection"], "clone-tests.tsv")
    evidence = {"spice_executable": str(executable), "spice_import": str(package),
                "prefix": str(prefix), "version": spice_lineage.__version__, "argv": argv}
    print("SPICE_GALAXY_EXECUTION " + json.dumps(evidence), flush=True)
    env = dict(os.environ, PYTHONNOUSERSITE="1")
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    os.execve(str(executable), [str(executable), *argv], env)


if __name__ == "__main__":
    main()
