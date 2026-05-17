#!/usr/bin/env python3
# ruff: noqa: E402, I001
"""Regenerate golden logs, AST snapshots, and expected_ticks in golden/*.json."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ast_format import format_program_ast
from isa import from_bytes
from control_unit import Machine
from translator import Compiler, parse, tokenize, write_program

GOLDEN_DIR = ROOT / "golden"


def regenerate_case(cfg_path: Path) -> None:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    name = cfg["name"]
    src = (ROOT / cfg["source"]).read_text(encoding="utf-8")
    input_tokens = list((ROOT / cfg["input"]).read_text(encoding="utf-8"))

    ast = parse(tokenize(src))
    program = Compiler().compile_program(ast)

    with tempfile.TemporaryDirectory() as td:
        out_bin = Path(td) / f"{name}.bin"
        write_program(str(out_bin), program)
        code = from_bytes(out_bin.read_bytes())
        data_payload = json.loads((Path(str(out_bin) + ".data.json")).read_text(encoding="utf-8"))
    machine = Machine(code, data_payload["data"], input_tokens)
    output, log = machine.run(limit=500000)

    log_name = f"{name}.log.txt"
    ast_name = f"{name}.ast.txt"
    (GOLDEN_DIR / log_name).write_text("\n".join(log) + "\n", encoding="utf-8")
    (GOLDEN_DIR / ast_name).write_text(format_program_ast(ast) + "\n", encoding="utf-8")

    cfg["log_file"] = log_name
    cfg["ast_file"] = ast_name
    cfg["expected_ticks"] = machine.state.tick
    cfg["required_log_contains"] = [
        "uPC=0 IR <- Mem[PC]",
        "uPC=1 uPC <- DECODER[IR.opcode]",
    ]
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assert output == cfg["expected_output"], f"{name}: output mismatch {output!r}"
    print(f"OK {name}: ticks={machine.state.tick} log_lines={len(log)}")


def main() -> None:
    for cfg_path in sorted(GOLDEN_DIR.glob("*.json")):
        if ".bin." in cfg_path.name:
            continue
        regenerate_case(cfg_path)


if __name__ == "__main__":
    main()
