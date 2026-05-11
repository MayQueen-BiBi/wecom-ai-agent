#!/usr/bin/env python3
"""
入口契约检查：禁止 WeCom 子模块导出 ``router``、禁止 ``app.agent``、禁止旧 orchestrator。

用法：``python scripts/check_entry_contract.py``（仓库根目录）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

BANNED_SUBSTRINGS = [
    "from app.wecom.handler import router",
    "from app.wecom.handler import router ",
    "wecom_router",
    "from app.agent",
    "import app.agent",
    "from app.agent.",
    "app.agent.core",
    "app.agent.orchestrator",
]


def scan_files() -> list[tuple[str, int, str]]:
    bad: list[tuple[str, int, str]] = []
    for path in sorted(APP.rglob("*.py")):
        if "guards" in path.parts and path.name == "dependency_guard.py":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            s = line.strip()
            if s.startswith("#"):
                continue
            for pat in BANNED_SUBSTRINGS:
                if pat in line:
                    bad.append((str(path.relative_to(ROOT)), i, pat))
                    break
    return bad


def wecom_must_not_define_router() -> list[str]:
    """``app/wecom`` 下不得再出现 ``APIRouter`` / ``router =`` 模式。"""
    errors: list[str] = []
    wecom = APP / "wecom"
    for path in sorted(wecom.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bAPIRouter\b", text):
            errors.append(f"{path.relative_to(ROOT)}: contains APIRouter")
        if re.search(r"^\s*router\s*=\s*APIRouter", text, re.MULTILINE):
            errors.append(f"{path.relative_to(ROOT)}: defines router = APIRouter")
    return errors


def main() -> int:
    bad = scan_files()
    bad.extend((p, 0, "wecom-router-ban") for p in wecom_must_not_define_router())
    if bad:
        print("entry contract check FAILED:\n")
        for path, lineno, detail in bad:
            print(f"  {path}:{lineno}: {detail}")
        return 1
    print("OK: entry contract (no banned imports / no wecom APIRouter).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
