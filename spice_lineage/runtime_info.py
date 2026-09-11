"""Runtime provenance; unavailable tools are recorded without blocking analysis."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from datetime import datetime, timezone

from . import __version__ as VERSION
from .paths import PACKAGE_DIR

ROOT = PACKAGE_DIR

def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def probe(command, timeout=30, env=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
        return {'returncode': result.returncode, 'output': (result.stdout + result.stderr)[:12000].strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'unavailable': str(exc)}

def git_probe(root, *arguments):
    # Git environment overrides must not associate SPICE with another checkout.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    return probe(["git", "-C", str(root), *arguments], env=env)


def checkout_root(package_dir):
    """Return a verified SPICE checkout, never an enclosing unrelated repo."""
    package_dir = Path(package_dir).resolve()
    root = package_dir.parent
    if (package_dir.name != "spice_lineage" or not (root / ".git").exists()
            or not all((root / name).is_file()
                       for name in ("SPICE.py", "VERSION", "pyproject.toml"))):
        return None
    top = git_probe(root, "rev-parse", "--show-toplevel")
    if top.get("returncode") != 0 or Path(top["output"]).resolve() != root:
        return None
    tracked = git_probe(root, "ls-files", "--error-unmatch", "SPICE.py", "VERSION")
    if tracked.get("returncode") != 0:
        return None
    return root


def source_provenance(package_dir):
    package_dir = Path(package_dir).resolve()
    source_files = [package_dir / "VERSION", *sorted(package_dir.glob("*.py")),
                    *sorted((package_dir / "resources" / "r").glob("*.R"))]
    hashes = {str(p.relative_to(package_dir.parent)): sha256(p) for p in source_files}
    checkout = checkout_root(package_dir)
    if checkout is None:
        unavailable = {"unavailable": "Running package is not in a SPICE Git checkout"}
        return {"source_root": str(package_dir), "source_sha256": hashes,
                "git_commit": unavailable.copy(), "git_status": unavailable.copy()}
    for name in ("SPICE.py", "VERSION"):
        hashes[name] = sha256(checkout / name)
    return {"source_root": str(package_dir), "source_sha256": hashes,
            "git_commit": git_probe(checkout, "rev-parse", "HEAD"),
            "git_status": git_probe(checkout, "status", "--porcelain")}


def capture_runtime(args, root):
    metadata = {'spice_version': VERSION, 'started_utc': datetime.now(timezone.utc).isoformat(),
                'command': args.command, 'parameters': {k:v for k,v in vars(args).items() if k!='func'},
                'python': platform.python_version(), 'platform': platform.platform(),
                'python_packages': {}, 'executables': {}}
    for name in ('pandas', 'numpy', 'pysam', 'tqdm'):
        try: metadata['python_packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: metadata['python_packages'][name] = None
    metadata.update(source_provenance(ROOT))
    rscript = shutil.which('Rscript')
    if rscript:
        code = 'cat(R.version.string,"\\n"); p <- installed.packages(); n <- intersect(c("ape","coda","janitor","posterior","dplyr","progress","phangorn","phytools","ggplot2","ggtree","ggsci"),rownames(p)); write.table(p[n,c("Package","Version"),drop=FALSE],row.names=FALSE,quote=FALSE,sep="\\t")'
        metadata['R'] = probe([rscript,'-e',code])
    else: metadata['R'] = {'unavailable': 'Rscript not found on PATH'}
    for name, env, aliases in [('BayesTraits','BAYESTRAITS_BIN',('BayesTraitsV4','BayesTraitsV4.1.3','BayesTraits')), ('IQ-TREE','IQTREE2_BIN',('iqtree2','iqtree'))]:
        explicit = getattr(args,'bayestraits_bin',None) if name=='BayesTraits' else None
        candidates = [explicit,os.environ.get(env),*aliases]
        binary = None
        for candidate in candidates:
            if not candidate: continue
            found = shutil.which(os.path.expanduser(candidate))
            if found:
                binary = str(Path(found).resolve());break
        info = {'path':binary}
        if binary:
            try: info['sha256'] = sha256(binary)
            except OSError as exc: info['hash_error'] = str(exc)
            # Executables records discovery, not execution. Standalone clones
            # must not launch IQ-TREE, including a provenance-only version probe.
            if name=='IQ-TREE' and args.command != 'clones':
                info['version_probe'] = probe([binary,'--version'])
        metadata['executables'][name] = info
    return metadata

def save_runtime(metadata, args, root, success):
    metadata['success'] = success
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    if hasattr(args,'output_directory'):
        directory = Path(args.output_directory).expanduser().resolve()
        name = args.prefix
    elif hasattr(args,'output'):
        output = Path(args.output).expanduser().resolve()
        directory, name = output.parent, output.name
    else: return
    # Read only the first line of retained BayesTraits stdout files, never execute
    # an interactive binary just to request its version.
    if directory.exists():
        for index, path in enumerate(directory.rglob('MCMC*.stdout.txt')):
            if index >= 6: break
            try:
                with path.open() as handle: line=handle.readline().strip()
                if line.startswith('BayesTraits'):
                    metadata['executables']['BayesTraits']['recorded_banner']=line
                    break
            except OSError: pass
    try:
        directory.mkdir(parents=True,exist_ok=True)
        path = directory/(name+'.runtime.json')
        if path.exists():path=directory/(name+'.runtime.'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.json')
        with path.open('x') as handle:json.dump(metadata,handle,indent=2)
    except OSError as exc:
        import warnings
        warnings.warn(f'Could not save runtime provenance: {exc}')
