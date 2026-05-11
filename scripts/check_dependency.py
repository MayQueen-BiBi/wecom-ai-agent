#!/usr/bin/env python3
"""
CI / 本地：依赖防火墙。等价于：

    python app/guards/dependency_guard.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "app" / "guards" / "dependency_guard.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        cwd=str(ROOT),
        check=False,
    )
    return int(proc.returncode)


if __name__ == "__main__":
    sys.exit(main())
