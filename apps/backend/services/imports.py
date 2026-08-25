"""
File-level import/dependency extraction via tree-sitter.

v1: nodes = files, edges = "A imports B". Externals kept as edge_type=external.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node

from services.chunking import EXT_TO_LANGUAGE, _get_parser

# Common stdlib / well-known roots treated as external without filesystem probe.
PYTHON_STDLIB_ROOTS = {
    "abc", "asyncio", "collections", "concurrent", "contextlib", "copy",
    "dataclasses", "datetime", "enum", "functools", "hashlib", "http",
    "importlib", "inspect", "io", "itertools", "json", "logging", "math",
    "os", "pathlib", "pickle", "re", "shutil", "socket", "sqlite3", "ssl",
    "string", "struct", "subprocess", "sys", "tempfile", "threading", "time",
    "typing", "unittest", "urllib", "uuid", "warnings", "weakref", "xml",
    "zipfile",
}

RUST_EXTERNAL_ROOTS = {"std", "core", "alloc", "proc_macro"}


@dataclass(frozen=True)
class RawDependency:
    from_file: str
    to_file: str | None
    edge_type: str  # import | reexport | external
    specifier: str


def _node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")


def _walk(node: Node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'`" and value[-1] == value[0]:
        return value[1:-1]
    return value


def _file_exists(repo_files: set[str], candidate: str) -> bool:
    return candidate in repo_files


def _resolve_with_extensions(repo_files: set[str], base: str) -> str | None:
    candidates = [
        base,
        f"{base}.ts",
        f"{base}.tsx",
        f"{base}.js",
        f"{base}.jsx",
        f"{base}.mjs",
        f"{base}.cjs",
        f"{base}/index.ts",
        f"{base}/index.tsx",
        f"{base}/index.js",
        f"{base}/index.jsx",
    ]
    for candidate in candidates:
        normalized = Path(candidate).as_posix()
        if _file_exists(repo_files, normalized):
            return normalized
    return None


def resolve_js_specifier(
    from_file: str,
    specifier: str,
    repo_files: set[str],
) -> tuple[str | None, str]:
    """Return (to_file | None, edge_type)."""
    if specifier.startswith("."):
        from_dir = Path(from_file).parent
        joined = (from_dir / specifier).as_posix()
        # Normalize .. segments without resolving outside repo conceptually.
        resolved = Path(joined)
        parts: list[str] = []
        for part in resolved.parts:
            if part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        base = "/".join(parts)
        hit = _resolve_with_extensions(repo_files, base)
        if hit:
            return hit, "import"
        return None, "external"
    # Bare / alias imports — external in v1 (path aliases not configured).
    return None, "external"


def resolve_python_specifier(
    from_file: str,
    module: str,
    *,
    level: int,
    repo_files: set[str],
) -> tuple[str | None, str]:
    if level > 0:
        # Relative: from ...pkg import x  → walk up `level` from from_file's package.
        parts = list(Path(from_file).parts[:-1])
        ups = level - 1
        if ups > len(parts):
            return None, "external"
        if ups:
            parts = parts[: len(parts) - ups]
        if module:
            parts.extend(module.split("."))
        base = "/".join(parts)
        for candidate in (f"{base}.py", f"{base}/__init__.py"):
            if candidate in repo_files:
                return candidate, "import"
        return None, "external"

    if not module:
        return None, "external"

    root = module.split(".", 1)[0]
    if root in PYTHON_STDLIB_ROOTS:
        return None, "external"

    parts = module.split(".")
    base = "/".join(parts)
    for candidate in (f"{base}.py", f"{base}/__init__.py"):
        if candidate in repo_files:
            return candidate, "import"
    return None, "external"


def resolve_rust_use(
    from_file: str,
    path_text: str,
    repo_files: set[str],
) -> tuple[str | None, str]:
    text = path_text.strip().removesuffix(";").strip()
    # Drop `as Alias` / `{...}` groups — take leading path only.
    text = text.split("{", 1)[0].strip().rstrip("::").strip()
    text = re.sub(r"\s+as\s+\w+$", "", text).strip()
    segments = [s for s in text.split("::") if s]
    if not segments:
        return None, "external"

    if segments[0] in RUST_EXTERNAL_ROOTS:
        return None, "external"

    if segments[0] == "crate":
        segments = segments[1:]
        # Locate crate root: nearest Cargo.toml ancestor → src/
        crate_src = _rust_crate_src(from_file, repo_files)
        if crate_src is None or not segments:
            return None, "external"
        # Map crate::foo::bar → src/foo/bar.rs or src/foo/mod.rs / src/foo.rs
        rel = "/".join(segments)
        for candidate in (
            f"{crate_src}/{rel}.rs",
            f"{crate_src}/{rel}/mod.rs",
            f"{crate_src}/{'/'.join(segments[:-1])}/{segments[-1]}.rs" if len(segments) > 1 else None,
        ):
            if candidate and candidate in repo_files:
                return candidate, "import"
        return None, "external"

    if segments[0] == "super":
        parent = Path(from_file).parent.parent.as_posix()
        rest = segments[1:]
        if not rest:
            return None, "external"
        rel = "/".join(rest)
        for candidate in (f"{parent}/{rel}.rs", f"{parent}/{rel}/mod.rs"):
            if candidate in repo_files:
                return candidate, "import"
        return None, "external"

    if segments[0] == "self":
        parent = Path(from_file).parent.as_posix()
        rest = segments[1:]
        if not rest:
            return None, "external"
        rel = "/".join(rest)
        for candidate in (f"{parent}/{rel}.rs", f"{parent}/{rel}/mod.rs"):
            if candidate and candidate in repo_files:
                return candidate, "import"
        return None, "external"

    # External crate.
    return None, "external"


def _rust_crate_src(from_file: str, repo_files: set[str]) -> str | None:
    parts = list(Path(from_file).parts[:-1])
    while True:
        prefix = "/".join(parts) if parts else ""
        cargo = f"{prefix}/Cargo.toml" if prefix else "Cargo.toml"
        # Cargo.toml may not be in repo_files (not a code file). Infer src/ instead.
        src = f"{prefix}/src" if prefix else "src"
        # Prefer an ancestor that has src/*.rs in the index.
        if any(f == src or f.startswith(src + "/") for f in repo_files):
            return src
        if not parts:
            break
        parts.pop()
    if any(f == "src" or f.startswith("src/") for f in repo_files):
        return "src"
    return None


def _extract_js_imports(source: bytes, root: Node) -> list[tuple[str, str]]:
    """Return list of (specifier, edge_type)."""
    out: list[tuple[str, str]] = []
    for node in _walk(root):
        if node.type in {"import_statement", "import_declaration"}:
            for child in _walk(node):
                if child.type == "string":
                    out.append((_strip_quotes(_node_text(source, child)), "import"))
                    break
        elif node.type == "export_statement":
            text = _node_text(source, node)
            if "from" not in text:
                continue
            for child in _walk(node):
                if child.type == "string":
                    out.append((_strip_quotes(_node_text(source, child)), "reexport"))
                    break
        elif node.type == "call_expression":
            fn = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if fn is None or args is None:
                continue
            fn_text = _node_text(source, fn)
            if fn_text not in {"require", "import"}:
                continue
            for child in args.children:
                if child.type == "string":
                    out.append((_strip_quotes(_node_text(source, child)), "import"))
                    break
    return out


def _extract_python_imports(source: bytes, root: Node) -> list[tuple[str, int, str]]:
    """Return list of (module, level, edge_type)."""
    out: list[tuple[str, int, str]] = []
    for node in _walk(root):
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    out.append((_node_text(source, child), 0, "import"))
                elif child.type == "aliased_import":
                    name = child.child_by_field_name("name")
                    if name is not None:
                        out.append((_node_text(source, name), 0, "import"))
        elif node.type == "import_from_statement":
            module = ""
            level = 0
            module_node = node.child_by_field_name("module_name")
            if module_node is not None and module_node.type == "relative_import":
                for child in module_node.children:
                    if child.type == "import_prefix":
                        level = _node_text(source, child).count(".")
                    elif child.type == "dotted_name":
                        module = _node_text(source, child)
            elif module_node is not None:
                module = _node_text(source, module_node)
            out.append((module, level, "import"))
    return out


def _extract_rust_uses(source: bytes, root: Node) -> list[str]:
    out: list[str] = []
    for node in _walk(root):
        if node.type == "use_declaration":
            out.append(_node_text(source, node).removeprefix("use").strip())
    return out


def extract_imports(
    file_path: str,
    content: str,
    language: str,
    repo_files: set[str],
) -> list[RawDependency]:
    parser = _get_parser(language)
    if parser is None:
        return []

    source = content.encode("utf-8")
    tree = parser.parse(source)
    deps: list[RawDependency] = []
    seen: set[tuple[str | None, str]] = set()

    if language in {"typescript", "javascript"}:
        for specifier, edge in _extract_js_imports(source, tree.root_node):
            to_file, resolved_edge = resolve_js_specifier(file_path, specifier, repo_files)
            if resolved_edge == "external":
                edge = "external"
                to_file = None
            key = (to_file or specifier, edge)
            if key in seen:
                continue
            seen.add(key)
            deps.append(
                RawDependency(
                    from_file=file_path,
                    to_file=to_file,
                    edge_type=edge,
                    specifier=specifier,
                )
            )
    elif language == "python":
        for module, level, edge in _extract_python_imports(source, tree.root_node):
            to_file, resolved_edge = resolve_python_specifier(
                file_path, module, level=level, repo_files=repo_files
            )
            if resolved_edge == "external":
                edge = "external"
                to_file = None
            key = (to_file or module, edge)
            if key in seen:
                continue
            seen.add(key)
            deps.append(
                RawDependency(
                    from_file=file_path,
                    to_file=to_file,
                    edge_type=edge,
                    specifier=module or "." * level,
                )
            )
    elif language == "rust":
        for use_path in _extract_rust_uses(source, tree.root_node):
            to_file, edge = resolve_rust_use(file_path, use_path, repo_files)
            key = (to_file or use_path, edge)
            if key in seen:
                continue
            seen.add(key)
            deps.append(
                RawDependency(
                    from_file=file_path,
                    to_file=to_file,
                    edge_type=edge,
                    specifier=use_path,
                )
            )

    return deps


def collect_repo_file_set(files: list[tuple[Path, str]], root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path, _ in files}


def language_for_path(file_path: str) -> str:
    return EXT_TO_LANGUAGE.get(Path(file_path).suffix.lower(), "unknown")
