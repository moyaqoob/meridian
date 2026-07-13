"""tree-sitter chunking at semantic boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Language, Parser

SKIP_DIRS = {"node_modules", "vendor", ".git", "dist", "build", "__pycache__", ".venv"}
SKIP_EXTENSIONS = {".lock", ".sum", ".mod", ".min.js", ".min.css"}
SUPPORTED_LANGUAGES = {"python", "typescript", "javascript"}
EXT_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}
TARGET_NODE_TYPES = {
    "python": {"function_definition", "class_definition", "decorated_definition"},
    "typescript": {"function_declaration", "method_definition", "class_declaration"},
    "javascript": {"function_declaration", "method_definition", "class_declaration"},
}

_parsers: dict[str, Parser] = {}


@dataclass
class RawChunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str


def should_index_file(path: str, language: str) -> bool:
    parts = Path(path).parts
    if any(part in SKIP_DIRS for part in parts):
        return False
    if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    if language not in SUPPORTED_LANGUAGES:
        return False
    return True


def _get_parser(language: str) -> Parser | None:
    if language in _parsers:
        return _parsers[language]

    try:
        if language == "python":
            import tree_sitter_python as lang_mod
        elif language == "typescript":
            import tree_sitter_typescript as lang_mod
        elif language == "javascript":
            import tree_sitter_javascript as lang_mod
        else:
            return None

        parser = Parser(Language(lang_mod.language()))
        _parsers[language] = parser
        return parser
    except Exception:
        return None


def _sliding_window_chunks(content: str, file_path: str, language: str) -> list[RawChunk]:
    lines = content.splitlines()
    window = 50
    overlap = 10
    chunks: list[RawChunk] = []

    for start in range(0, len(lines), max(window - overlap, 1)):
        block = "\n".join(lines[start : start + window])
        if len(block.strip()) < 20:
            continue
        chunks.append(
            RawChunk(
                content=block,
                file_path=file_path,
                start_line=start + 1,
                end_line=min(start + window, len(lines)),
                language=language,
            )
        )
    return chunks


def _walk_meaningful_nodes(node, language: str):
    targets = TARGET_NODE_TYPES.get(language, set())
    if node.type in targets:
        yield node
        return
    for child in node.children:
        yield from _walk_meaningful_nodes(child, language)


def parse_file(content: str, file_path: str, language: str) -> list[RawChunk]:
    parser = _get_parser(language)
    if parser is None:
        return _sliding_window_chunks(content, file_path, language)

    tree = parser.parse(content.encode("utf-8"))
    chunks: list[RawChunk] = []

    for node in _walk_meaningful_nodes(tree.root_node, language):
        chunk_text = content[node.start_byte : node.end_byte]
        if len(chunk_text.strip()) < 20:
            continue
        chunks.append(
            RawChunk(
                content=chunk_text,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language,
            )
        )

    if not chunks:
        return _sliding_window_chunks(content, file_path, language)
    return chunks


def iter_repo_files(repo_path: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_path).as_posix()
        language = EXT_TO_LANGUAGE.get(path.suffix.lower())
        if not language or not should_index_file(rel_path, language):
            continue
        files.append((path, language))
    return files
