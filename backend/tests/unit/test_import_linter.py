"""Verify import-linter contracts are wired and enforced."""

import shutil
import subprocess
import sys
from pathlib import Path


def test_import_linter_passes_on_clean_tree() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    lint_imports = shutil.which("lint-imports")
    command = [lint_imports] if lint_imports else [sys.executable, "-m", "lint_imports"]
    result = subprocess.run(
        command,
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
