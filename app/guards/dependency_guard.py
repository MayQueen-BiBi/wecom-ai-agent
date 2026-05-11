"""
依赖防火墙：扫描 ``app/**/*.py`` 的 import，**禁止**任何 ``app.agent`` 依赖。

Phase 7 后 ``app/agent`` 已移除；若重新引入该包，也不得被 ``app/`` 下其它代码引用。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

FORBIDDEN_PREFIX = "app.agent"


def _file_imports_agent(tree: ast.AST) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == FORBIDDEN_PREFIX or alias.name.startswith(
                    FORBIDDEN_PREFIX + "."
                ):
                    hits.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module
            if mod == FORBIDDEN_PREFIX or (
                mod and mod.startswith(FORBIDDEN_PREFIX + ".")
            ):
                hits.append((node.lineno, mod or ""))
    return hits


def scan_dependency_violations(root: Path | None = None) -> list[tuple[str, int, str]]:
    """
    返回违规列表 ``(relative_path, lineno, detail)``。
    空列表表示通过。
    """
    root = root or Path(__file__).resolve().parents[2]
    app_dir = root / "app"
    violations: list[tuple[str, int, str]] = []

    for path in sorted(app_dir.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError as e:
            violations.append((rel, e.lineno or 0, f"SyntaxError: {e}"))
            continue

        for lineno, mod in _file_imports_agent(tree):
            violations.append((rel, lineno, f"import {mod}"))

    return violations


def check_dependency_graph() -> bool:
    """返回 ``True`` 表示依赖图合法（``app/`` 内无任何 ``app.agent`` import）。"""
    return not scan_dependency_violations()


def main() -> int:
    bad = scan_dependency_violations()
    if bad:
        print("Dependency guard FAILED:\n")
        for path, lineno, detail in bad:
            print(f"  {path}:{lineno}: {detail}")
        return 1
    print("OK: no app.agent imports under app/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
