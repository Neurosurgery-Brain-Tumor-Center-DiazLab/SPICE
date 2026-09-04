import os
import sys
import shutil
import subprocess
from pathlib import Path

def iqtree2_command(fasta_path: str, output_directory: str, sample_id: str,
                    model: str, uf_bootstrap: int, sh_alrt: int,
                    threads: int | None) -> str:
    """
    Build an IQ-TREE2 command string from CLI arguments.

    Notes
    -----
    - If 'threads' is None, IQ-TREE2 will use AUTO threading.
    - 'model' maps to '-m'.
    - 'uf_bootstrap' maps to '-B'.
    - 'sh_alrt' maps to '--alrt'.
    """
    #fasta_file = os.path.join(output_directory, f"{sample_id}.SNV_mat.filter.fasta")
    fasta_file = fasta_path

    # Resolve IQ-TREE2 binary from env var or system PATH
    iqtree2_bin = os.environ.get("IQTREE2_BIN")
    
    if iqtree2_bin:
        if not (os.path.isfile(iqtree2_bin) and os.access(iqtree2_bin, os.X_OK)):
            raise RuntimeError(
                    f"IQTREE2_BIN is set but is not a valid executable: {iqtree2_bin}"
            )
        
    else:
        iqtree2_bin = shutil.which("iqtree2")
        
    if iqtree2_bin is None:
        iqtree2_bin = shutil.which("iqtree")
        
    if iqtree2_bin is None:
        raise RuntimeError(
            "IQ-TREE2 executable was not found. "
            "Install IQ-TREE2 and ensure 'iqtree2' is available in PATH, "
            "or set the IQTREE2_BIN environment variable."
        )

    # Threads: use user-provided integer or AUTO
    thread_token = str(threads) if (threads is not None and threads > 0) else "AUTO"

    cmd = (
        f"{iqtree2_bin} "
        f"-s {fasta_file} "
        f"-T {thread_token} "
        f"-B {int(uf_bootstrap)} "
        f"--alrt {int(sh_alrt)} "
        f"-m {model}"
    )
    return cmd

def generate_script(script_content: str, output_directory: str, sample_id: str) -> str:
    """
    Write a small shell script to disk and make it executable.
    """
    script_path = os.path.join(output_directory, f"{sample_id}_iqtree2.sh")
    with open(script_path, "w") as fh:
        #fh.write("#!/usr/bin/env bash\nset -euo pipefail\n")
        fh.write("#!/usr/bin/env bash\n")
        fh.write(script_content.strip() + "\n")
    os.chmod(script_path, 0o755)
    return script_path
