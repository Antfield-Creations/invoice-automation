import subprocess
import sys


def test_module_entry_point_help():
    result = subprocess.run(
        [sys.executable, '-m', 'invoice_automation', '--help'],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert 'usage' in result.stdout
