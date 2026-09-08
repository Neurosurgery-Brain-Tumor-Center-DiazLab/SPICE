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

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()

def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def probe(command, timeout=30):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {'returncode': result.returncode, 'output': (result.stdout + result.stderr)[:12000].strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'unavailable': str(exc)}

def capture_runtime(args, root):
    metadata = {'spice_version': VERSION, 'started_utc': datetime.now(timezone.utc).isoformat(),
                'command': args.command, 'parameters': {k:v for k,v in vars(args).items() if k!='func'},
                'python': platform.python_version(), 'platform': platform.platform(),
                'python_packages': {}, 'executables': {}}
    for name in ('pandas', 'numpy', 'pysam', 'tqdm'):
        try: metadata['python_packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: metadata['python_packages'][name] = None
    source_files = [root/'SPICE.py', root/'VERSION', *sorted((root/'scripts').glob('*.py')), *sorted((root/'scripts').glob('*.R'))]
    metadata['source_sha256'] = {str(p.relative_to(root)):sha256(p) for p in source_files}
    metadata['git_commit'] = probe(['git','-C',str(root),'rev-parse','HEAD'])
    metadata['git_status'] = probe(['git','-C',str(root),'status','--porcelain'])
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
            if name=='IQ-TREE':info['version_probe'] = probe([binary,'--version'])
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
