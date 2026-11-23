"""Thin wrapper around the official Proton Drive CLI (`proton-drive`).

Used to fetch the members spreadsheet and to archive generated invoices
in Proton Drive. Member data never enters the git repository.
"""
import subprocess
from pathlib import Path
from typing import List

CLI = 'proton-drive'


def _run(args: List[str]) -> str:
    result = subprocess.run([CLI, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"`{CLI} {' '.join(args)}` failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def download(remote_path: str, local_dir: str | Path) -> Path:
    """Download a single file from Proton Drive into local_dir."""
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    _run(['filesystem', 'download', remote_path, str(local_dir)])
    return local_dir / Path(remote_path).name


def upload(local_path: str | Path, remote_dir: str) -> None:
    """Upload a file or folder to a Proton Drive folder."""
    _run(['filesystem', 'upload', str(local_path), remote_dir])
