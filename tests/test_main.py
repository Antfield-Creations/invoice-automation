import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_module_entry_point_help():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / 'src' / 'main.py'), '--help'],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert 'usage' in result.stdout
