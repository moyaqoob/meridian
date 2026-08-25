"""Import resolution unit tests."""

from __future__ import annotations

from services.imports import (
    extract_imports,
    resolve_js_specifier,
    resolve_python_specifier,
)


def test_resolve_js_relative() -> None:
    files = {"src/a.ts", "src/b.ts", "src/lib/util.ts"}
    to_file, edge = resolve_js_specifier("src/a.ts", "./b", files)
    assert edge == "import"
    assert to_file == "src/b.ts"

    to_file, edge = resolve_js_specifier("src/a.ts", "./lib/util", files)
    assert to_file == "src/lib/util.ts"

    to_file, edge = resolve_js_specifier("src/a.ts", "react", files)
    assert edge == "external"
    assert to_file is None


def test_resolve_python_relative_and_stdlib() -> None:
    files = {"pkg/__init__.py", "pkg/a.py", "pkg/b.py"}
    to_file, edge = resolve_python_specifier(
        "pkg/a.py", "b", level=1, repo_files=files
    )
    assert edge == "import"
    assert to_file == "pkg/b.py"

    to_file, edge = resolve_python_specifier(
        "pkg/a.py", "os", level=0, repo_files=files
    )
    assert edge == "external"


def test_extract_ts_imports() -> None:
    content = """
import React from 'react';
import { helper } from './util';
export { helper } from './util';
"""
    files = {"src/index.ts", "src/util.ts"}
    deps = extract_imports("src/index.ts", content, "typescript", files)
    by_spec = {d.specifier: d for d in deps}
    assert by_spec["react"].edge_type == "external"
    assert by_spec["./util"].to_file == "src/util.ts"
    assert by_spec["./util"].edge_type in {"import", "reexport"}


def test_extract_python_imports() -> None:
    content = """
import os
from .b import thing
from pkg.c import x
"""
    files = {"pkg/a.py", "pkg/b.py", "pkg/c.py"}
    deps = extract_imports("pkg/a.py", content, "python", files)
    edges = {(d.specifier, d.edge_type, d.to_file) for d in deps}
    assert ("os", "external", None) in edges
    assert any(d.to_file == "pkg/b.py" for d in deps)
