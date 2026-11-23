import subprocess

import pytest

from invoice_automation import drive


class _Result:
    def __init__(self, returncode=0, stdout='ok', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_download_invokes_cli_and_returns_local_path(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        subprocess, 'run',
        lambda args, **kw: calls.append(args) or _Result(),
    )

    path = drive.download('/Leden/leden.csv', tmp_path / 'work')

    assert calls == [['proton-drive', 'filesystem', 'download', '/Leden/leden.csv', str(tmp_path / 'work')]]
    assert path == tmp_path / 'work' / 'leden.csv'


def test_upload_invokes_cli(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        subprocess, 'run',
        lambda args, **kw: calls.append(args) or _Result(),
    )

    drive.upload(tmp_path / 'out', '/Facturen/2026/5')

    assert calls == [['proton-drive', 'filesystem', 'upload', str(tmp_path / 'out'), '/Facturen/2026/5']]


def test_cli_failure_raises_runtime_error(monkeypatch):
    monkeypatch.setattr(
        subprocess, 'run',
        lambda args, **kw: _Result(returncode=1, stderr='not logged in'),
    )

    with pytest.raises(RuntimeError, match='not logged in'):
        drive.download('/Leden/leden.csv', '/tmp/x')
