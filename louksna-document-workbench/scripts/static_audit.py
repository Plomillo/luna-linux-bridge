#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "src" / "louksna_docworkbench"
    failures = []
    checked = []
    for path in sorted(src.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            failures.append({"file": str(path.relative_to(root)), "rule": "PYTHON_SYNTAX", "detail": str(exc)})
            continue
        checked.append(str(path.relative_to(root)))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any("document_factory" in name or "document-factory" in name for name in names):
                    failures.append({
                        "file": str(path.relative_to(root)),
                        "rule": "DOCUMENT_FACTORY_DEPENDENCY_FORBIDDEN",
                        "line": getattr(node, "lineno", None),
                    })
            if isinstance(node, ast.Call):
                is_subprocess_run = (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                )
                if is_subprocess_run:
                    shell = next((keyword.value for keyword in node.keywords if keyword.arg == "shell"), None)
                    if not isinstance(shell, ast.Constant) or shell.value is not False:
                        failures.append({
                            "file": str(path.relative_to(root)),
                            "rule": "SUBPROCESS_SHELL_MUST_BE_FALSE",
                            "line": node.lineno,
                        })
        if re.search(r"https?://", text):
            failures.append({
                "file": str(path.relative_to(root)),
                "rule": "NETWORK_ENDPOINT_LITERAL_REVIEW",
                "detail": "Literal URL in runtime code requires explicit review.",
            })

    report = {
        "schema": "LOUKSNA_DOCUMENT_WORKBENCH_STATIC_AUDIT/1.0",
        "status": "PASS" if not failures else "FAIL",
        "python_files_checked": checked,
        "rules": [
            "Python syntax parses",
            "No import dependency on Document Factory",
            "Any subprocess.run call must set shell=False literally",
            "Runtime Python modules contain no literal HTTP(S) endpoints",
        ],
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
