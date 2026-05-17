"""Human-readable AST formatting for lab4 Lisp translator."""

from __future__ import annotations

from typing import Any


def format_ast(node: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(node, int):
        return str(node)
    if isinstance(node, str):
        if node in {"block", "begin", "progn"}:
            return node
        escaped = node.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(node, list):
        if not node:
            return "()"
        head = node[0]
        if head in {"block", "begin", "progn"}:
            lines = [f"{pad}({head}"]
            for item in node[1:]:
                lines.append(f"{pad}  {format_ast(item, indent + 1)}")
            lines.append(f"{pad})")
            return "\n".join(lines)
        inner = " ".join(format_ast(x, indent) for x in node)
        return f"({inner})"
    return str(node)


def format_program_ast(ast: list[Any]) -> str:
    if len(ast) == 1:
        return format_ast(ast[0])
    lines = ["(begin"]
    for node in ast:
        lines.append(f"  {format_ast(node, 1)}")
    lines.append(")")
    return "\n".join(lines)
