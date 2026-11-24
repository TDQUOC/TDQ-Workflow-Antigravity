#!/usr/bin/env python3
"""TDQ Archify Logic Node Registry & 2-Layer AST Symbol Hashing Module.

Provides:
- TREE_SITTER_PACKAGES & check_tree_sitter_support: inspect tree-sitter and grammar availability.
- extract_symbol_ast_hash: compute comment/docstring-invariant, offset-free AST SHA-256 + live span_binding.
- validate_logic_node: fail-closed schema and path-safety validation for Logic Nodes.
- detect_cycles: bounded DFS cycle detection with visited_stack and DAG reuse support.
- compute_dirty_set: compare live AST hashes & spans against registry nodes and relink span shifts.
- sync_registry_index: synchronize registry/index.json and enforce planned-node isolation.

Env: TDQ_LOG=0 silences ISO-timestamped stderr logs (enabled by default).
"""
from __future__ import annotations

import ast
import copy
import datetime
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

TREE_SITTER_PACKAGES: tuple[str, ...] = (
    "tree-sitter",
    "tree-sitter-python",
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-rust",
)

_PACKAGE_MODULES: tuple[tuple[str, str], ...] = (
    ("tree-sitter", "tree_sitter"),
    ("tree-sitter-python", "tree_sitter_python"),
    ("tree-sitter-javascript", "tree_sitter_javascript"),
    ("tree-sitter-typescript", "tree_sitter_typescript"),
    ("tree-sitter-rust", "tree_sitter_rust"),
)

_EXT_LANG_MAP: dict[str, tuple[str, str, str]] = {
    ".py": ("python", "tree_sitter_python", "language"),
    ".pyi": ("python", "tree_sitter_python", "language"),
    ".js": ("javascript", "tree_sitter_javascript", "language"),
    ".mjs": ("javascript", "tree_sitter_javascript", "language"),
    ".cjs": ("javascript", "tree_sitter_javascript", "language"),
    ".jsx": ("javascript", "tree_sitter_javascript", "language"),
    ".ts": ("typescript", "tree_sitter_typescript", "language_typescript"),
    ".mts": ("typescript", "tree_sitter_typescript", "language_typescript"),
    ".cts": ("typescript", "tree_sitter_typescript", "language_typescript"),
    ".tsx": ("tsx", "tree_sitter_typescript", "language_tsx"),
    ".rs": ("rust", "tree_sitter_rust", "language"),
}

_COMMENT_NODE_TYPES = frozenset({"comment", "line_comment", "block_comment"})
_VALID_TIERS = frozenset({"eager_l1_l2", "lazy_l3_plus"})
_VALID_EVIDENCE = frozenset({"planned", "working-tree", "committed"})
_VALID_CACHE_STATUS = frozenset({"clean", "span_shifted_only", "dirty", "planned_draft"})
_VALID_HASH_MODES = frozenset({"tree_sitter_ast", "python_ast", "file_fallback"})
_VALID_LANES = frozenset({"main", "branch", "error"})
_VALID_NODE_KINDS = frozenset({
    "flow_root",
    "ui_action",
    "decision_branch",
    "security_crypto",
    "storage_io",
    "network_rpc",
    "error_handler",
    "gate_check",
    "registry_op",
    "portal_render",
})
_NODE_ALLOWED_KEYS = frozenset({
    "node_id",
    "title",
    "depth",
    "node_kind",
    "hydration_tier",
    "evidence_kind",
    "fingerprint",
    "natural_explanation",
    "io_contract",
    "sub_flow",
    "sources",
    "reused_by",
})
_FP_ALLOWED_KEYS = frozenset({
    "symbol_ref",
    "ast_symbol_sha256",
    "span_binding",
    "render_slice_sha256",
    "cache_status",
    "hash_mode",
})
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

_DECL_NODE_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"function_definition", "class_definition"}),
    "javascript": frozenset({
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "method_definition",
        "variable_declarator",
    }),
    "typescript": frozenset({
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "abstract_class_declaration",
        "method_definition",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
        "function_signature",
        "variable_declarator",
    }),
    "tsx": frozenset({
        "function_declaration",
        "generator_function_declaration",
        "class_declaration",
        "abstract_class_declaration",
        "method_definition",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
        "function_signature",
        "variable_declarator",
    }),
    "rust": frozenset({
        "function_item",
        "function_signature_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "mod_item",
        "type_item",
        "const_item",
        "static_item",
        "macro_definition",
    }),
}

_CONTAINER_NODE_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"class_definition", "function_definition"}),
    "javascript": frozenset({"class_declaration", "class"}),
    "typescript": frozenset({"class_declaration", "abstract_class_declaration", "class", "module"}),
    "tsx": frozenset({"class_declaration", "abstract_class_declaration", "class", "module"}),
    "rust": frozenset({"impl_item", "trait_item", "mod_item"}),
}

_FN_VALUE_TYPES = frozenset({
    "arrow_function",
    "function_expression",
    "function",
    "generator_function",
})


def _log_enabled() -> bool:
    """Return True unless stderr logging is disabled via TDQ_LOG=0."""
    return os.environ.get("TDQ_LOG", "1") != "0"


def _log(message: str) -> None:
    """Emit one ISO-timestamped log line to stderr."""
    if _log_enabled():
        stamp = datetime.datetime.now().replace(microsecond=0).isoformat()
        print(f"[{stamp}] archify_registry: {message}", file=sys.stderr)


def _is_safe_relative_path(path_str: Any) -> bool:
    """Check that path_str is a relative path without traversal, drive letters, or NUL bytes."""
    if not isinstance(path_str, str):
        return False
    clean = path_str.strip()
    if not clean or "\0" in clean or ":" in clean:
        return False
    norm = clean.replace("\\", "/")
    if norm.startswith("/"):
        return False
    return ".." not in norm.split("/")


def _is_within(path: Path, parent: Path) -> bool:
    """Return True when resolved path lies inside resolved parent."""
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _atomic_write_json(target: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically via temp file in target directory."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, target)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _probe_module(pkg: str, mod_name: str) -> tuple[bool, str | None]:
    """Try importing one tree-sitter module and reading its package version."""
    try:
        importlib.import_module(mod_name)
    except (ImportError, OSError, RuntimeError, ValueError):
        return False, None
    try:
        return True, importlib.metadata.version(pkg)
    except (importlib.metadata.PackageNotFoundError, OSError, ValueError):
        return True, None


def _available_languages(modules_ok: dict[str, bool]) -> list[str]:
    """Return language identifiers enabled by available modules."""
    if not modules_ok.get("tree_sitter"):
        return []
    langs: list[str] = []
    if modules_ok.get("tree_sitter_python"):
        langs.append("python")
    if modules_ok.get("tree_sitter_javascript"):
        langs.append("javascript")
    if modules_ok.get("tree_sitter_typescript"):
        langs.extend(["typescript", "tsx"])
    if modules_ok.get("tree_sitter_rust"):
        langs.append("rust")
    return langs


def check_tree_sitter_support() -> dict[str, Any]:
    """Inspect installation state of tree-sitter core and language grammar packages."""
    modules_ok: dict[str, bool] = {}
    versions: dict[str, str | None] = {}
    missing: list[str] = []
    installed: list[str] = []

    for pkg, mod_name in _PACKAGE_MODULES:
        ok, ver = _probe_module(pkg, mod_name)
        modules_ok[mod_name] = ok
        versions[pkg] = ver
        if ok:
            installed.append(pkg)
        else:
            missing.append(pkg)

    result = {
        "available": len(missing) == 0,
        "missing": missing,
        "installed": installed,
        "modules": modules_ok,
        "versions": versions,
        "languages": _available_languages(modules_ok),
        "version": versions.get("tree-sitter"),
    }
    _log(f"checked tree-sitter support: available={result['available']} missing={missing}")
    return result


def _load_ts_parser(ext: str) -> tuple[str, Any] | None:
    """Load (lang_name, Parser) for a supported file extension, or return None."""
    spec = _EXT_LANG_MAP.get(ext.lower())
    if spec is None:
        return None
    lang_name, mod_name, fn_name = spec
    try:
        ts_mod = importlib.import_module("tree_sitter")
        lang_mod = importlib.import_module(mod_name)
        lang_factory = getattr(lang_mod, fn_name)
        language = ts_mod.Language(lang_factory())
        parser = ts_mod.Parser(language)
    except (ImportError, AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        _log(f"tree-sitter parser unavailable for {ext}: {exc}")
        return None
    return lang_name, parser


def _node_text(node: Any) -> str:
    """Decode UTF-8 text from a tree-sitter node safely."""
    raw = getattr(node, "text", b"")
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


def _rust_impl_target(node: Any) -> str:
    """Extract the base struct/enum type name from a Rust impl_item."""
    type_node = node.child_by_field_name("type")
    if type_node is None:
        return ""
    if type_node.type == "generic_type":
        inner = type_node.child_by_field_name("type")
        if inner is not None:
            return _node_text(inner)
    return _node_text(type_node)


def _match_symbol_name(node: Any, lang_name: str) -> str | None:
    """Return declared symbol name when node is a supported declaration, else None."""
    if node.type not in _DECL_NODE_TYPES.get(lang_name, ()):
        return None
    if node.type == "variable_declarator":
        val = node.child_by_field_name("value")
        if val is None or val.type not in _FN_VALUE_TYPES:
            return None
    name_node = node.child_by_field_name("name")
    return _node_text(name_node) if name_node is not None else None


def _container_name(node: Any, lang_name: str) -> str | None:
    """Return container name for classes, traits, modules, or Rust impl blocks."""
    if node.type not in _CONTAINER_NODE_TYPES.get(lang_name, ()):
        return None
    if lang_name == "rust" and node.type == "impl_item":
        return _rust_impl_target(node)
    name_node = node.child_by_field_name("name")
    return _node_text(name_node) if name_node is not None else None


def _find_ts_declarations(root: Any, lang_name: str, target: str) -> list[Any]:
    """Find declaration nodes matching target name inside root subtree."""
    matches: list[Any] = []
    stack = [root]
    while stack:
        curr = stack.pop()
        if _match_symbol_name(curr, lang_name) == target:
            matches.append(curr)
        stack.extend(reversed(curr.children))
    return matches


def _find_ts_containers(root: Any, lang_name: str, target: str) -> list[Any]:
    """Find container nodes matching target name inside root subtree."""
    matches: list[Any] = []
    stack = [root]
    while stack:
        curr = stack.pop()
        if _container_name(curr, lang_name) == target:
            matches.append(curr)
        stack.extend(reversed(curr.children))
    return matches


def _find_ts_symbol(root: Any, lang_name: str, symbol: str) -> Any | None:
    """Resolve top-level or qualified (Class.method) symbol in a tree-sitter tree."""
    parts = [p for p in symbol.replace("::", ".").split(".") if p]
    if not parts:
        return None
    scopes = [root]
    for part in parts[:-1]:
        next_scopes: list[Any] = []
        for scope in scopes:
            next_scopes.extend(_find_ts_containers(scope, lang_name, part))
        if not next_scopes:
            return None
        scopes = next_scopes
    for scope in scopes:
        found = _find_ts_declarations(scope, lang_name, parts[-1])
        if found:
            return found[0]
    return None


def _is_py_docstring(node: Any, container_type: str | None) -> bool:
    """Return True if node is a leading Python docstring expression_statement."""
    if container_type not in ("function_definition", "class_definition", "module"):
        return False
    if node.type != "expression_statement":
        return False
    named = [ch for ch in node.children if ch.type not in _COMMENT_NODE_TYPES]
    return len(named) == 1 and named[0].type in ("string", "concatenated_string")


def _walk_ts_tokens(
    node: Any,
    lang_name: str,
    tokens: list[tuple[str, ...]],
    *,
    container_type: str | None = None,
    is_first_stmt: bool = False,
) -> None:
    """Append offset-free AST structural tokens while stripping comments and docstrings."""
    if node.type in _COMMENT_NODE_TYPES:
        return
    if lang_name == "python" and is_first_stmt and _is_py_docstring(node, container_type):
        return
    if node.child_count == 0:
        tokens.append(("L", node.type, _node_text(node)))
        return
    tokens.append(("(", node.type))
    seen_stmt = False
    if node.type in ("function_definition", "class_definition", "module"):
        child_owner: str | None = node.type
    elif node.type == "block":
        child_owner = container_type
    else:
        child_owner = None
    for child in node.children:
        if child.type in _COMMENT_NODE_TYPES:
            continue
        first = node.type in ("block", "module") and not seen_stmt and child.is_named
        if first:
            seen_stmt = True
        _walk_ts_tokens(child, lang_name, tokens, container_type=child_owner, is_first_stmt=first)
    tokens.append((")", node.type))


def _hash_ts_node(node: Any, lang_name: str) -> str:
    """Compute SHA-256 over normalized AST tokens of node (or its decorated wrapper)."""
    target = node.parent if getattr(getattr(node, "parent", None), "type", None) == "decorated_definition" else node
    tokens: list[tuple[str, ...]] = []
    _walk_ts_tokens(target, lang_name, tokens)
    digest = hashlib.sha256()
    for item in tokens:
        digest.update(repr(item).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _node_line_span(node: Any) -> tuple[int, int]:
    """Convert tree-sitter 0-based row/col points into 1-based inclusive line span."""
    start_line = int(node.start_point.row) + 1
    end_row = int(node.end_point.row)
    end_col = int(node.end_point.column)
    end_line = end_row if end_col == 0 and end_row > node.start_point.row else end_row + 1
    return start_line, max(start_line, end_line)


def _strip_py_ast_docstrings(node: ast.AST) -> ast.AST:
    """Return a copy of Python AST node with leading docstrings stripped."""
    cloned = copy.deepcopy(node)
    body_types = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for sub in ast.walk(cloned):
        if isinstance(sub, body_types) and sub.body:
            first = sub.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                sub.body = sub.body[1:]
    return cloned


def _find_py_ast_symbol(tree: ast.AST, parts: list[str]) -> ast.AST | None:
    """Find top-level or Class.method node in Python stdlib AST."""
    scopes: list[ast.AST] = [tree]
    decl_types = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for idx, part in enumerate(parts):
        is_last = idx == len(parts) - 1
        next_scopes: list[ast.AST] = []
        for scope in scopes:
            for child in ast.iter_child_nodes(scope):
                if isinstance(child, decl_types) and child.name == part:
                    if is_last:
                        return child
                    next_scopes.append(child)
        if not next_scopes:
            return None
        scopes = next_scopes
    return None


def _extract_via_python_ast(source_text: str, file_path: Path, symbol: str) -> dict[str, Any] | None:
    """Fallback AST extractor using Python stdlib ast module."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None
    parts = [p for p in symbol.replace("::", ".").split(".") if p]
    node = _find_py_ast_symbol(tree, parts) if parts else None
    if node is None:
        return None
    normalized = _strip_py_ast_docstrings(node)
    dumped = ast.dump(normalized, include_attributes=False)
    digest = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
    start_line = int(getattr(node, "lineno", 1))
    end_line = int(getattr(node, "end_lineno", None) or start_line)
    return {
        "symbol": symbol,
        "ast_symbol_sha256": digest,
        "span_binding": {
            "path": file_path.as_posix(),
            "line": start_line,
            "end_line": max(start_line, end_line),
        },
        "hash_mode": "python_ast",
        "language": "python",
        "symbol_found": True,
    }


def _extract_file_fallback(raw_bytes: bytes, file_path: Path, symbol: str) -> dict[str, Any]:
    """Compute transparent file-level fallback hash when AST symbol parsing cannot match."""
    normalized = raw_bytes.replace(b"\r\n", b"\n")
    digest = hashlib.sha256(normalized).hexdigest()
    line_count = max(1, len(normalized.splitlines()))
    return {
        "symbol": symbol,
        "ast_symbol_sha256": digest,
        "span_binding": {
            "path": file_path.as_posix(),
            "line": 1,
            "end_line": line_count,
        },
        "hash_mode": "file_fallback",
        "language": file_path.suffix.lower().lstrip(".") or "unknown",
        "symbol_found": False,
    }


def extract_symbol_ast_hash(file_path: Path, symbol: str) -> dict[str, Any]:
    """Compute 2-layer AST symbol SHA-256 and live span_binding for a source symbol."""
    target_path = Path(file_path)
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")
    clean_symbol = symbol.strip()
    if not target_path.is_file():
        raise FileNotFoundError(f"Source file not found: {target_path}")

    raw_bytes = target_path.read_bytes().replace(b"\r\n", b"\n")
    ext = target_path.suffix.lower()
    loaded = _load_ts_parser(ext)

    if loaded is not None:
        lang_name, parser = loaded
        tree = parser.parse(raw_bytes)
        sym_node = _find_ts_symbol(tree.root_node, lang_name, clean_symbol)
        if sym_node is not None:
            start_line, end_line = _node_line_span(sym_node)
            return {
                "symbol": clean_symbol,
                "ast_symbol_sha256": _hash_ts_node(sym_node, lang_name),
                "span_binding": {
                    "path": target_path.as_posix(),
                    "line": start_line,
                    "end_line": end_line,
                },
                "hash_mode": "tree_sitter_ast",
                "language": lang_name,
                "symbol_found": True,
            }

    if ext in (".py", ".pyi") and loaded is None:
        py_res = _extract_via_python_ast(raw_bytes.decode("utf-8", errors="replace"), target_path, clean_symbol)
        if py_res is not None:
            return py_res

    fallback = _extract_file_fallback(raw_bytes, target_path, clean_symbol)
    _log(f"fallback hash for {target_path.as_posix()}::{clean_symbol} ({fallback['hash_mode']})")
    return fallback


def _is_int(value: Any) -> bool:
    """Return True strictly for int values (excluding bool)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    """Ensure value is a dict, raising ValueError for schema consumers."""
    if type(value) is not dict:
        raise ValueError(f"{label} must be a dictionary")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    """Ensure value is a list, raising ValueError for schema consumers."""
    if type(value) is not list:
        raise ValueError(f"{label} must be a list")
    return value


def _validate_span_dict(span: Any, label: str) -> None:
    """Validate {path, line, end_line} span object."""
    span_dict = _require_dict(span, label)
    if not _is_safe_relative_path(span_dict.get("path")):
        raise ValueError(f"{label}.path must be a safe relative path: {span_dict.get('path')!r}")
    line = span_dict.get("line")
    end_line = span_dict.get("end_line")
    if not _is_int(line) or not _is_int(end_line) or line < 1 or end_line < line:
        raise ValueError(f"{label} invalid line range: {line}..{end_line}")


def _validate_node_identity(node: dict[str, Any]) -> None:
    """Validate top-level Logic Node keys, ID, title, depth, tier, and evidence_kind."""
    unknown = set(node) - _NODE_ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Unexpected Logic Node fields: {sorted(unknown)}")
    node_id = node.get("node_id")
    if not isinstance(node_id, str) or not _ID_RE.fullmatch(node_id):
        raise ValueError(f"Invalid node_id: {node_id!r}")
    title = node.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"Node '{node_id}' title must be a non-empty string")
    depth = node.get("depth")
    if not _is_int(depth) or depth < 1 or depth > 8:
        raise ValueError(f"Node '{node_id}' depth must be an integer 1..8, got {depth!r}")
    if "node_kind" in node and node["node_kind"] not in _VALID_NODE_KINDS:
        raise ValueError(f"Node '{node_id}' invalid node_kind: {node['node_kind']!r}")
    if node.get("hydration_tier") not in _VALID_TIERS:
        raise ValueError(f"Node '{node_id}' invalid hydration_tier: {node.get('hydration_tier')!r}")
    if node.get("evidence_kind") not in _VALID_EVIDENCE:
        raise ValueError(f"Node '{node_id}' invalid evidence_kind: {node.get('evidence_kind')!r}")


def _validate_fingerprint(fp: Any, node_id: str) -> None:
    """Validate Logic Node fingerprint object."""
    fp_dict = _require_dict(fp, f"Node '{node_id}' fingerprint")
    required = {"symbol_ref", "ast_symbol_sha256", "span_binding", "render_slice_sha256", "cache_status"}
    missing = required - set(fp_dict)
    if missing:
        raise ValueError(f"Node '{node_id}' fingerprint missing fields: {sorted(missing)}")
    unknown = set(fp_dict) - _FP_ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Node '{node_id}' fingerprint has unexpected fields: {sorted(unknown)}")
    if not isinstance(fp_dict["symbol_ref"], str) or not fp_dict["symbol_ref"].strip():
        raise ValueError(f"Node '{node_id}' fingerprint.symbol_ref must be non-empty")
    sha = fp_dict["ast_symbol_sha256"]
    if sha is not None and (not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha)):
        raise ValueError(f"Node '{node_id}' invalid ast_symbol_sha256: {sha!r}")
    _validate_span_dict(fp_dict["span_binding"], f"{node_id}.fingerprint.span_binding")
    if fp_dict["render_slice_sha256"] is not None and not isinstance(fp_dict["render_slice_sha256"], str):
        raise ValueError(f"Node '{node_id}' render_slice_sha256 must be string or null")
    if fp_dict["cache_status"] not in _VALID_CACHE_STATUS:
        raise ValueError(f"Node '{node_id}' invalid cache_status: {fp_dict['cache_status']!r}")
    if "hash_mode" in fp_dict and fp_dict["hash_mode"] is not None and fp_dict["hash_mode"] not in _VALID_HASH_MODES:
        raise ValueError(f"Node '{node_id}' invalid hash_mode: {fp_dict['hash_mode']!r}")


def _validate_str_list(items: Any, label: str) -> None:
    """Ensure items is a list of strings."""
    if not isinstance(items, list) or not all(isinstance(x, str) for x in items):
        raise ValueError(f"{label} must be a list of strings")


def _validate_prose_and_io(node: dict[str, Any], node_id: str) -> None:
    """Validate natural_explanation and io_contract structures."""
    ne = _require_dict(node.get("natural_explanation"), f"Node '{node_id}' natural_explanation")
    if set(ne) != {"summary", "what_goes_where", "why_it_exists", "edge_cases"}:
        raise ValueError(
            f"Node '{node_id}' natural_explanation requires summary, what_goes_where, why_it_exists, edge_cases"
        )
    for key in ("summary", "what_goes_where", "why_it_exists"):
        if not isinstance(ne[key], str) or not ne[key].strip():
            raise ValueError(f"Node '{node_id}' natural_explanation.{key} must be non-empty string")
    _validate_str_list(ne["edge_cases"], f"{node_id}.natural_explanation.edge_cases")

    io_c = _require_dict(node.get("io_contract"), f"Node '{node_id}' io_contract")
    if set(io_c) != {"inputs", "outputs", "side_effects"}:
        raise ValueError(f"Node '{node_id}' io_contract requires inputs, outputs, side_effects")
    for key in ("inputs", "outputs", "side_effects"):
        _validate_str_list(io_c[key], f"{node_id}.io_contract.{key}")


def _validate_sub_flow_steps(steps: Any, node_id: str) -> set[str]:
    """Validate sub_flow step list and return collected step_ids."""
    step_list = _require_list(steps, f"Node '{node_id}' sub_flow.steps")
    if not (1 <= len(step_list) <= 6):
        raise ValueError(f"Node '{node_id}' sub_flow.steps must contain 1..6 steps")
    step_ids: set[str] = set()
    for step in step_list:
        step_dict = _require_dict(step, f"Node '{node_id}' sub_flow step")
        if not step_dict.get("step_id") or not step_dict.get("label"):
            raise ValueError(f"Node '{node_id}' sub_flow step missing step_id or label")
        sid = str(step_dict["step_id"])
        if sid in step_ids:
            raise ValueError(f"Node '{node_id}' duplicate sub_flow step_id: {sid!r}")
        step_ids.add(sid)
        col = step_dict.get("col")
        if not _is_int(col) or col < 0 or col > 5:
            raise ValueError(f"Node '{node_id}' step '{sid}' col must be 0..5")
        if "lane" in step_dict and step_dict["lane"] not in _VALID_LANES:
            raise ValueError(f"Node '{node_id}' step '{sid}' invalid lane: {step_dict['lane']!r}")
    return step_ids


def _validate_sub_flow_edges(edges: Any, step_ids: set[str], node_id: str) -> None:
    """Validate sub_flow edges against defined step_ids."""
    edge_list = _require_list(edges, f"Node '{node_id}' sub_flow.edges")
    for edge in edge_list:
        if not isinstance(edge, dict) or edge.get("from") not in step_ids or edge.get("to") not in step_ids:
            raise ValueError(f"Node '{node_id}' sub_flow edge references unknown step: {edge!r}")


def _validate_sub_flow(sub_flow: Any, node_id: str) -> None:
    """Validate optional sub_flow slice layout, steps (<= 6), and edges."""
    sf_dict = _require_dict(sub_flow, f"Node '{node_id}' sub_flow")
    if set(sf_dict) != {"slice_id", "max_cols", "steps", "edges"}:
        raise ValueError(f"Node '{node_id}' sub_flow requires slice_id, max_cols, steps, edges")
    slice_id = sf_dict["slice_id"]
    if not isinstance(slice_id, str) or not _ID_RE.fullmatch(slice_id):
        raise ValueError(f"Node '{node_id}' invalid sub_flow.slice_id: {slice_id!r}")
    max_cols = sf_dict["max_cols"]
    if not _is_int(max_cols) or max_cols < 1 or max_cols > 6:
        raise ValueError(f"Node '{node_id}' sub_flow.max_cols must be 1..6")
    step_ids = _validate_sub_flow_steps(sf_dict["steps"], node_id)
    _validate_sub_flow_edges(sf_dict["edges"], step_ids, node_id)


def _validate_sources_and_reuse(node: dict[str, Any], node_id: str) -> None:
    """Validate sources (1..3) and reused_by (>= 1)."""
    sources = _require_list(node.get("sources"), f"Node '{node_id}' sources")
    if not (1 <= len(sources) <= 3):
        raise ValueError(f"Node '{node_id}' sources must contain 1..3 entries")
    for idx, src in enumerate(sources):
        _validate_span_dict(src, f"{node_id}.sources[{idx}]")
    reused_by = _require_list(node.get("reused_by"), f"Node '{node_id}' reused_by")
    if not reused_by or not all(isinstance(x, str) and x.strip() for x in reused_by):
        raise ValueError(f"Node '{node_id}' reused_by must be a non-empty list of strings")


def validate_logic_node(node: dict[str, Any]) -> dict[str, Any]:
    """Validate one Logic Node against the canonical registry schema."""
    node_dict = _require_dict(node, "Logic Node")
    _validate_node_identity(node_dict)
    node_id = node_dict["node_id"]
    _validate_fingerprint(node_dict.get("fingerprint"), node_id)
    _validate_prose_and_io(node_dict, node_id)
    _validate_sources_and_reuse(node_dict, node_id)
    if "sub_flow" in node_dict:
        _validate_sub_flow(node_dict["sub_flow"], node_id)
    return node_dict


def _record_cycle(
    cycles: list[dict[str, Any]],
    seen: set[tuple[str, str, str]],
    record: dict[str, Any],
) -> None:
    """Record a unique cycle descriptor into cycles."""
    key = (record["from_node"], record["to_node"], record["step_id"])
    if key not in seen:
        seen.add(key)
        cycles.append(record)


def _collect_step_targets(node: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    """Extract (step_id, target_node_id, cycle_back_to) tuples from a node's sub_flow."""
    sub_flow = node.get("sub_flow")
    if not isinstance(sub_flow, dict):
        return []
    return [
        (str(step.get("step_id", "")), step.get("target_node_id"), step.get("cycle_back_to"))
        for step in sub_flow.get("steps", [])
    ]


def _reachable_nodes(nodes: dict[str, dict[str, Any]], start: str) -> set[str]:
    """Compute nodes reachable from start within the graph."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        curr = stack.pop()
        if curr in seen or curr not in nodes:
            continue
        seen.add(curr)
        for _, target_id, _ in _collect_step_targets(nodes[curr]):
            if target_id and target_id not in seen:
                stack.append(target_id)
    return seen


def detect_cycles(
    nodes: dict[str, dict[str, Any]],
    root_id: str,
    max_depth: int = 6,
) -> list[dict[str, Any]]:
    """Detect cycles reachable from root_id using DFS visited_stack bounded by max_depth."""
    if not _is_int(max_depth) or max_depth < 1:
        raise ValueError(f"max_depth must be a positive integer, got {max_depth!r}")
    if root_id not in nodes:
        _log(f"detect_cycles: root_id '{root_id}' not present in nodes")
        return []

    reach_cache = {nid: _reachable_nodes(nodes, nid) for nid in nodes}
    cycles: list[dict[str, Any]] = []
    seen_cycles: set[tuple[str, str, str]] = set()
    explored_clean: set[str] = set()
    visited_stack: list[str] = []

    def _dfs(curr_id: str, depth: int) -> None:
        visited_stack.append(curr_id)
        stack_set = set(visited_stack)
        for step_id, target_id, back_id in _collect_step_targets(nodes[curr_id]):
            if back_id:
                _record_cycle(cycles, seen_cycles, {
                    "from_node": curr_id, "to_node": back_id,
                    "detected_at_depth": depth, "handling": "anchor-back-to-breadcrumb",
                    "step_id": step_id, "via": "cycle_back_to",
                })
            if not target_id:
                continue
            if target_id in stack_set:
                _record_cycle(cycles, seen_cycles, {
                    "from_node": curr_id, "to_node": target_id,
                    "detected_at_depth": depth, "handling": "anchor-back-to-breadcrumb",
                    "step_id": step_id, "via": "visited_stack",
                })
                continue
            can_prune = target_id in explored_clean and not (reach_cache.get(target_id, set()) & stack_set)
            if depth < max_depth and target_id in nodes and not can_prune:
                _dfs(target_id, depth + 1)
        visited_stack.pop()
        explored_clean.add(curr_id)

    _dfs(root_id, 1)
    return cycles


def _resolve_symbol_name(symbol_ref: str) -> str:
    """Normalize symbol_ref into exact symbol name for AST extraction."""
    raw = symbol_ref.strip()
    if "::" in raw:
        left, right = raw.split("::", 1)
        is_path_prefix = "/" in left or "\\" in left or "." in left or ":" in left
        if is_path_prefix:
            return right.strip().replace("::", ".")
        return raw.replace("::", ".")
    if ":" in raw:
        return raw.split(":", 1)[1].strip()
    return raw


def _collect_registry_files(registry_dir: Path) -> tuple[list[Path], dict[str, Any] | None]:
    """Collect validated Logic Node file paths from index.json and nodes/*.json."""
    index_path = registry_dir / "index.json"
    existing_index: dict[str, Any] | None = None
    candidate_files: dict[Path, bool] = {}

    if index_path.is_file():
        existing_index = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in existing_index.get("nodes", []):
            rel = entry.get("file_path")
            if not isinstance(rel, str):
                continue
            if not _is_safe_relative_path(rel):
                raise ValueError(f"Unsafe node file_path in index.json: {rel!r}")
            p = (registry_dir / rel).resolve()
            if not _is_within(p, registry_dir):
                raise ValueError(f"Node file_path escapes registry_dir: {rel!r}")
            candidate_files[p] = True

    nodes_dir = registry_dir / "nodes"
    if nodes_dir.is_dir():
        for p in sorted(nodes_dir.glob("*.json")):
            candidate_files[p.resolve()] = True
    return sorted(candidate_files), existing_index


def _load_registry_nodes(
    registry_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path], dict[str, Any] | None]:
    """Load and validate all Logic Node files inside registry_dir."""
    if not registry_dir.is_dir():
        raise FileNotFoundError(f"Registry directory not found: {registry_dir}")
    file_paths, existing_index = _collect_registry_files(registry_dir)
    nodes: dict[str, dict[str, Any]] = {}
    node_paths: dict[str, Path] = {}
    for file_path in file_paths:
        if not file_path.is_file():
            raise FileNotFoundError(f"Referenced Logic Node file not found: {file_path}")
        node_data = validate_logic_node(json.loads(file_path.read_text(encoding="utf-8")))
        nid = node_data["node_id"]
        if nid in nodes:
            raise ValueError(f"Duplicate node_id '{nid}' in registry: {file_path}")
        nodes[nid] = node_data
        node_paths[nid] = file_path
    return nodes, node_paths, existing_index


def _update_matching_sources(node: dict[str, Any], old_span: dict[str, Any], new_span: dict[str, Any]) -> None:
    """Update matching source entry spans in place after line shifts."""
    for src in node.get("sources", []):
        if src.get("path") == old_span.get("path") and src.get("line") == old_span.get("line"):
            src["line"] = new_span["line"]
            src["end_line"] = new_span["end_line"]


def _relink_node_span_files(
    registry_dir: Path,
    node: dict[str, Any],
    node_path: Path,
    old_span: dict[str, Any],
    new_span: dict[str, Any],
) -> None:
    """Persist relinked span_binding and cache_status='span_shifted_only' into node.json and index.json."""
    node["fingerprint"]["span_binding"] = dict(new_span)
    node["fingerprint"]["cache_status"] = "span_shifted_only"
    _update_matching_sources(node, old_span, new_span)
    _atomic_write_json(node_path, node)

    index_path = registry_dir / "index.json"
    if not index_path.is_file():
        return
    idx_data = json.loads(index_path.read_text(encoding="utf-8"))
    updated = False
    for entry in idx_data.get("nodes", []):
        if entry.get("node_id") == node["node_id"]:
            entry["span_binding"] = dict(new_span)
            entry["cache_status"] = "span_shifted_only"
            updated = True
    if updated:
        _atomic_write_json(index_path, idx_data)


def _resolve_node_source_file(node: dict[str, Any], project_root: Path) -> tuple[str, Path] | None:
    """Resolve safe source file path inside project_root for a Logic Node."""
    rel_path = node["fingerprint"]["span_binding"]["path"]
    if not _is_safe_relative_path(rel_path):
        return None
    full_path = (project_root / rel_path).resolve()
    if not _is_within(full_path, project_root) or not full_path.is_file():
        return None
    return Path(rel_path).as_posix(), full_path


def _evaluate_non_planned_node(
    node: dict[str, Any],
    node_path: Path,
    registry_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Compare live AST hash & span against stored fingerprint for one non-planned node."""
    fp = node["fingerprint"]
    slice_id = node.get("sub_flow", {}).get("slice_id")
    resolved = _resolve_node_source_file(node, project_root)
    if resolved is None:
        return {
            "cache_status": "dirty",
            "reason": "missing_or_unsafe_source",
            "slice_id": slice_id,
            "ast_symbol_sha256": fp.get("ast_symbol_sha256"),
            "span_binding": fp.get("span_binding"),
            "hash_mode": fp.get("hash_mode", "file_fallback"),
        }

    rel_posix, abs_src = resolved
    sym_name = _resolve_symbol_name(fp["symbol_ref"])
    extracted = extract_symbol_ast_hash(abs_src, sym_name)
    new_span = {**extracted["span_binding"], "path": rel_posix}
    new_hash = extracted["ast_symbol_sha256"]
    old_hash = fp.get("ast_symbol_sha256")
    old_span = fp.get("span_binding")

    if old_hash != new_hash:
        status = "dirty"
    elif old_span != new_span:
        status = "span_shifted_only"
        _relink_node_span_files(registry_dir, node, node_path, old_span, new_span)
    else:
        status = "clean"

    return {
        "cache_status": status,
        "slice_id": slice_id,
        "ast_symbol_sha256": new_hash,
        "span_binding": new_span,
        "hash_mode": extracted["hash_mode"],
    }


def compute_dirty_set(registry_dir: Path, project_root: Path) -> dict[str, Any]:
    """Compute dirty nodes, affected slices, and relinked span-shifted nodes."""
    reg_root = Path(registry_dir).resolve()
    proj_root = Path(project_root).resolve()
    nodes, node_paths, _ = _load_registry_nodes(reg_root)

    dirty_nodes: list[str] = []
    dirty_slices: list[str] = []
    span_shifted: list[str] = []
    clean_nodes: list[str] = []
    planned_nodes: list[str] = []
    statuses: dict[str, dict[str, Any]] = {}

    for nid in sorted(nodes):
        node = nodes[nid]
        if node["evidence_kind"] == "planned":
            planned_nodes.append(nid)
            statuses[nid] = {
                "cache_status": "planned_draft",
                "slice_id": node.get("sub_flow", {}).get("slice_id"),
            }
            continue

        info = _evaluate_non_planned_node(node, node_paths[nid], reg_root, proj_root)
        statuses[nid] = info
        status = info["cache_status"]
        if status == "dirty":
            dirty_nodes.append(nid)
            if info["slice_id"] and info["slice_id"] not in dirty_slices:
                dirty_slices.append(info["slice_id"])
        elif status == "span_shifted_only":
            span_shifted.append(nid)
        else:
            clean_nodes.append(nid)

    _log(
        f"dirty set computed: total={len(nodes)} dirty={len(dirty_nodes)} "
        f"shifted={len(span_shifted)} clean={len(clean_nodes)}"
    )
    return {
        "dirty_nodes": dirty_nodes,
        "dirty_slices": sorted(dirty_slices),
        "span_shifted_nodes": span_shifted,
        "clean_nodes": clean_nodes,
        "planned_nodes": planned_nodes,
        "node_statuses": statuses,
    }


def _summary_sha256(node: dict[str, Any]) -> str:
    """Hash natural_explanation + io_contract deterministically."""
    payload = {
        "natural_explanation": node["natural_explanation"],
        "io_contract": node["io_contract"],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _detect_all_cycles(nodes: dict[str, dict[str, Any]], max_depth: int) -> tuple[list[str], list[dict[str, Any]]]:
    """Identify root flows and detect cycles across all flow roots."""
    roots = [
        nid for nid, node in sorted(nodes.items())
        if node.get("depth") == 1 or node.get("node_kind") == "flow_root"
    ]
    if not roots and nodes:
        roots = [min(nodes)]

    all_cycles: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for root_id in roots:
        for cyc in detect_cycles(nodes, root_id, max_depth=max_depth):
            key = (cyc["from_node"], cyc["to_node"], cyc.get("step_id", ""))
            if key not in seen_keys:
                seen_keys.add(key)
                all_cycles.append(cyc)
    return roots, all_cycles


def _sync_single_node(node: dict[str, Any], node_path: Path, project_root: Path) -> None:
    """Refresh live AST hash and span_binding on a non-planned Logic Node file."""
    if node["evidence_kind"] == "planned":
        return
    nid = node["node_id"]
    resolved = _resolve_node_source_file(node, project_root)
    if resolved is None:
        raise FileNotFoundError(
            f"Source file missing or unsafe for node '{nid}': {node['fingerprint']['span_binding']['path']}"
        )
    rel_posix, abs_src = resolved
    extracted = extract_symbol_ast_hash(abs_src, _resolve_symbol_name(node["fingerprint"]["symbol_ref"]))
    new_span = {**extracted["span_binding"], "path": rel_posix}
    old_span = node["fingerprint"]["span_binding"]
    node["fingerprint"]["ast_symbol_sha256"] = extracted["ast_symbol_sha256"]
    node["fingerprint"]["hash_mode"] = extracted["hash_mode"]
    node["fingerprint"]["span_binding"] = new_span
    node["fingerprint"]["cache_status"] = "clean"
    _update_matching_sources(node, old_span, new_span)
    _atomic_write_json(node_path, node)


def _build_index_entry(node: dict[str, Any], node_path: Path, reg_root: Path) -> dict[str, Any]:
    """Build compact index.json entry for a Logic Node."""
    return {
        "node_id": node["node_id"],
        "title": node["title"],
        "depth": node["depth"],
        "node_kind": node.get("node_kind", "decision_branch"),
        "hydration_tier": node["hydration_tier"],
        "evidence_kind": node["evidence_kind"],
        "symbol_ref": node["fingerprint"]["symbol_ref"],
        "ast_symbol_sha256": node["fingerprint"]["ast_symbol_sha256"],
        "hash_mode": node["fingerprint"].get("hash_mode"),
        "span_binding": node["fingerprint"]["span_binding"],
        "summary_sha256": _summary_sha256(node),
        "sub_flow_slice_id": node.get("sub_flow", {}).get("slice_id"),
        "reused_by": list(node["reused_by"]),
        "cache_status": node["fingerprint"]["cache_status"],
        "file_path": node_path.relative_to(reg_root).as_posix(),
    }


def sync_registry_index(
    registry_dir: Path,
    project_root: Path,
    include_planned: bool = False,
) -> dict[str, Any]:
    """Sync Logic Node hashes/spans from disk and write registry/index.json."""
    reg_root = Path(registry_dir).resolve()
    proj_root = Path(project_root).resolve()
    nodes, node_paths, existing_index = _load_registry_nodes(reg_root)

    if not include_planned:
        planned_ids = [nid for nid, n in sorted(nodes.items()) if n["evidence_kind"] == "planned"]
        if planned_ids:
            raise ValueError(
                f"Refusing to sync planned node(s) into master registry with include_planned=False: {planned_ids}"
            )

    max_depth = int(existing_index.get("max_depth", 6)) if existing_index else 6
    index_entries: list[dict[str, Any]] = []
    for nid in sorted(nodes):
        _sync_single_node(nodes[nid], node_paths[nid], proj_root)
        index_entries.append(_build_index_entry(nodes[nid], node_paths[nid], reg_root))

    root_flows, cycles = _detect_all_cycles(nodes, max_depth)
    index_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "max_depth": max_depth,
        "root_flows": root_flows,
        "node_count": len(index_entries),
        "cycles_detected": cycles,
        "nodes": index_entries,
    }
    _atomic_write_json(reg_root / "index.json", index_payload)
    _log(f"synced registry index: nodes={len(index_entries)} cycles={len(cycles)} include_planned={include_planned}")
    return index_payload
