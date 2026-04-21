#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any

from isa import Instruction, Opcode, to_bytes, to_hex_listing

PORT_IN = 0
PORT_OUT = 1


def tokenize(source: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(source):
        c = source[i]
        if c.isspace():
            i += 1
            continue
        if c == ";":
            # Lisp-style single-line comment.
            while i < len(source) and source[i] != "\n":
                i += 1
            continue
        if c in "(){}[]":
            tokens.append(c)
            i += 1
            continue
        if c == '"':
            j = i + 1
            buf = ['"']
            while j < len(source):
                ch = source[j]
                buf.append(ch)
                if ch == '"' and source[j - 1] != "\\":
                    break
                j += 1
            tokens.append("".join(buf))
            i = j + 1
            continue
        j = i
        while j < len(source) and (not source[j].isspace()) and source[j] not in "(){}[]":
            j += 1
        tokens.append(source[i:j])
        i = j
    return tokens


def parse(tokens: list[str]):
    def read(pos: int):
        token = tokens[pos]
        if token == "(":
            pos += 1
            out = []
            while tokens[pos] != ")":
                node, pos = read(pos)
                out.append(node)
            return out, pos + 1
        if token == "{":
            pos += 1
            out = ["block"]
            while tokens[pos] != "}":
                node, pos = read(pos)
                out.append(node)
            return out, pos + 1
        if token == "[":
            name = tokens[pos + 1]
            node, end_pos = read(pos + 2)
            assert tokens[end_pos] == "]"
            return ["aref", name, node], end_pos + 1
        if token.startswith('"') and token.endswith('"'):
            text = bytes(token[1:-1], "utf-8").decode("unicode_escape")
            return ["str", text], pos + 1
        if token.lstrip("-").isdigit():
            return int(token), pos + 1
        return token, pos + 1

    ast = []
    pos = 0
    while pos < len(tokens):
        node, pos = read(pos)
        ast.append(node)
    return ast


@dataclass
class Program:
    code: list[Instruction]
    data: list[int]
    data_labels: dict[str, int]
    ast: Any


class Compiler:
    def __init__(self):
        self.code: list[Instruction] = []
        self.data: list[int] = []
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []
        self.globals: dict[str, int] = {}
        self.consts: dict[int, int] = {}
        self.strings: dict[str, int] = {}
        self.functions: dict[str, tuple[list[str], list]] = {}
        self.tmp0 = self.alloc_global("__tmp0")
        self.tmp1 = self.alloc_global("__tmp1")
        self.tmp2 = self.alloc_global("__tmp2")

    def alloc_data(self, value: int = 0) -> int:
        idx = len(self.data)
        self.data.append(value)
        return idx

    def alloc_const(self, value: int) -> int:
        if value not in self.consts:
            self.consts[value] = self.alloc_data(value)
        return self.consts[value]

    def alloc_global(self, name: str) -> int:
        if name not in self.globals:
            self.globals[name] = self.alloc_data(0)
        return self.globals[name]

    def alloc_pstr(self, text: str) -> int:
        if text in self.strings:
            return self.strings[text]
        base = self.alloc_data(len(text))
        for ch in text:
            self.alloc_data(ord(ch))
        self.strings[text] = base
        return base

    def emit(self, opcode: Opcode, arg: int = 0):
        self.code.append(Instruction(opcode, arg))

    def emit_jump(self, opcode: Opcode, label: str):
        idx = len(self.code)
        self.code.append(Instruction(opcode, 0))
        self.fixups.append((idx, label))

    def place_label(self, label: str):
        self.labels[label] = len(self.code)

    def resolve(self, env: dict[str, int], name: str):
        if name in env:
            return ("local", env[name])
        return ("global", self.alloc_global(name))

    def compile_expr(self, node, env: dict[str, int]):
        if isinstance(node, int):
            self.emit(Opcode.LOADI, node)
            return
        if isinstance(node, list) and node and node[0] == "str":
            # String literal as expression: return base address of pstr.
            base = self.alloc_pstr(node[1])
            self.emit(Opcode.LOADI, base)
            return
        if isinstance(node, str):
            kind, slot = self.resolve(env, node)
            self.emit(Opcode.LOAD_LOCAL if kind == "local" else Opcode.LOAD, slot)
            return
        if not node:
            self.emit(Opcode.LOADI, 0)
            return

        head = node[0]
        if head in {"block", "begin", "progn"}:
            for x in node[1:]:
                self.compile_expr(x, env)
            return
        if head in {"assign", "setq", "set"}:
            _, name, expr = node
            self.compile_expr(expr, env)
            kind, slot = self.resolve(env, name)
            self.emit(Opcode.STORE_LOCAL if kind == "local" else Opcode.STORE, slot)
            # assignment is an expression: leave assigned value in ACC
            self.emit(Opcode.LOAD_LOCAL if kind == "local" else Opcode.LOAD, slot)
            return
        if head in {"check", "if"}:
            _, cond, then_body, *rest = node
            else_body = rest[0] if rest else 0
            else_lbl = f"else_{len(self.code)}"
            end_lbl = f"end_{len(self.code)}"
            self.compile_expr(cond, env)
            self.emit_jump(Opcode.JZ, else_lbl)
            self.compile_expr(then_body, env)
            self.emit_jump(Opcode.JMP, end_lbl)
            self.place_label(else_lbl)
            self.compile_expr(else_body, env)
            self.place_label(end_lbl)
            return
        if head in {"repeat", "loop"}:
            # (loop cond body) -- while cond do body
            # (repeat body)    -- do body while ACC != 0 (legacy)
            if head == "repeat":
                _, body = node
                start_lbl = f"repeat_{len(self.code)}"
                self.place_label(start_lbl)
                self.compile_expr(body, env)
                self.emit_jump(Opcode.JNZ, start_lbl)
                return
            if len(node) == 2:
                _, body = node
                start_lbl = f"loop_{len(self.code)}"
                self.place_label(start_lbl)
                self.compile_expr(body, env)
                self.emit_jump(Opcode.JNZ, start_lbl)
                return
            _, cond, body = node
            start_lbl = f"loop_{len(self.code)}"
            end_lbl = f"loop_end_{len(self.code)}"
            self.place_label(start_lbl)
            self.compile_expr(cond, env)
            self.emit_jump(Opcode.JZ, end_lbl)
            self.compile_expr(body, env)
            self.emit_jump(Opcode.JMP, start_lbl)
            self.place_label(end_lbl)
            self.emit(Opcode.LOADI, 0)
            return
        if head in {"+", "-", "*", "/", "%"}:
            operands = node[1:]
            if not operands:
                self.emit(Opcode.LOADI, 0)
                return
            if len(operands) == 1:
                self.compile_expr(operands[0], env)
                return
            a = operands[0]
            b = operands[1]
            self.compile_expr(a, env)
            self.emit(Opcode.PUSH, 0)
            self.compile_expr(b, env)
            self.emit(Opcode.STORE, self.tmp1)
            self.emit(Opcode.POP, self.tmp0)
            op = {"+": Opcode.ADD, "-": Opcode.SUB, "*": Opcode.MUL, "/": Opcode.DIV, "%": Opcode.MOD}[head]
            self.emit(op, self.tmp1)
            for extra in operands[2:]:
                self.emit(Opcode.PUSH, 0)
                self.compile_expr(extra, env)
                self.emit(Opcode.STORE, self.tmp1)
                self.emit(Opcode.POP, self.tmp0)
                self.emit(op, self.tmp1)
            return
        if head in {"=", ">", "<", ">=", "<=", "!="}:
            _, a, b = node
            self.compile_expr(a, env)
            self.emit(Opcode.PUSH, 0)
            self.compile_expr(b, env)
            self.emit(Opcode.STORE, self.tmp1)
            self.emit(Opcode.POP, self.tmp0)
            self.emit(Opcode.CMP, self.tmp1)
            if head == "=":
                return
            if head == "!=":
                true_lbl = f"ne_true_{len(self.code)}"
                end_lbl = f"ne_end_{len(self.code)}"
                self.emit_jump(Opcode.JZ, true_lbl)
                self.emit(Opcode.LOADI, 0)
                self.emit_jump(Opcode.JMP, end_lbl)
                self.place_label(true_lbl)
                self.emit(Opcode.LOADI, 1)
                self.place_label(end_lbl)
                return
            true_lbl = f"cmp_true_{len(self.code)}"
            false_lbl = f"cmp_false_{len(self.code)}"
            end_lbl = f"cmp_end_{len(self.code)}"
            if head == ">":
                self.emit_jump(Opcode.JG, true_lbl)
                self.emit_jump(Opcode.JMP, false_lbl)
            elif head == "<":
                self.emit_jump(Opcode.JL, true_lbl)
                self.emit_jump(Opcode.JMP, false_lbl)
            elif head == ">=":
                self.emit_jump(Opcode.JL, false_lbl)
                self.emit_jump(Opcode.JMP, true_lbl)
            elif head == "<=":
                self.emit_jump(Opcode.JG, false_lbl)
                self.emit_jump(Opcode.JMP, true_lbl)

            self.place_label(true_lbl)
            self.emit(Opcode.LOADI, 1)
            self.emit_jump(Opcode.JMP, end_lbl)
            self.place_label(false_lbl)
            self.emit(Opcode.LOADI, 0)
            self.place_label(end_lbl)
            return
        if head == "in":
            _, port = node
            self.emit(Opcode.IN, port)
            return
        if head == "out":
            _, port, expr = node
            self.compile_expr(expr, env)
            self.emit(Opcode.OUT, port)
            return
        if head == "print":
            # Minimal user-level print helper.
            if len(node) != 2:
                raise ValueError("print expects one argument")
            expr = node[1]
            if isinstance(expr, list) and expr and expr[0] == "str":
                for ch in expr[1]:
                    self.emit(Opcode.LOADI, ord(ch))
                    self.emit(Opcode.OUT, PORT_OUT)
                return
            self.compile_expr(expr, env)
            self.emit(Opcode.OUT, PORT_OUT)
            return
        if head == "aref":
            _, arr_name, idx_expr = node
            self.compile_expr(idx_expr, env)
            self.emit(Opcode.STORE, self.tmp0)
            base = self.alloc_global(arr_name)
            self.emit(Opcode.LOAD, base)
            return
        if isinstance(head, str) and head in self.functions:
            args = node[1:]
            for arg_expr in args:
                self.compile_expr(arg_expr, env)
                self.emit(Opcode.PUSH, 0)
            self.emit(Opcode.LOADI, len(args))
            self.emit(Opcode.PUSH, 0)
            self.emit_jump(Opcode.CALL, f"func_{head}")
            return

        raise ValueError(f"Unsupported expression: {node}")

    def compile_func(self, name: str, params: list[str], body):
        label = f"func_{name}"
        self.place_label(label)
        env = {p: i for i, p in enumerate(params)}
        self.compile_expr(body, env)
        self.emit(Opcode.RET, 0)

    def compile_program(self, ast) -> Program:
        top_level = []
        for st in ast:
            if isinstance(st, list) and st and st[0] in {"func", "defun"}:
                _, fn_name, params_list, *body_parts = st
                params = params_list if isinstance(params_list, list) else []
                body = body_parts[0] if len(body_parts) == 1 else ["begin", *body_parts]
                self.functions[fn_name] = (params, body)
            else:
                top_level.append(st)

        for st in top_level:
            self.compile_expr(st, {})
        self.emit(Opcode.HALT, 0)

        for fn_name, (params, body) in self.functions.items():
            self.compile_func(fn_name, params, body)

        for idx, label in self.fixups:
            self.code[idx].arg = self.labels[label]
        return Program(self.code, self.data, {**self.globals, **self.strings}, ast)


def write_program(path: str, program: Program):
    binary = to_bytes(program.code)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(binary)
    with open(path + ".hex", "w", encoding="utf-8") as f:
        f.write(to_hex_listing(program.code))
    with open(path + ".data.json", "w", encoding="utf-8") as f:
        json.dump({"data": program.data, "labels": program.data_labels}, f, ensure_ascii=False, indent=2)
    with open(path + ".ast.json", "w", encoding="utf-8") as f:
        json.dump(program.ast, f, ensure_ascii=False, indent=2)


def main(src_path: str, out_path: str):
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    tokens = tokenize(src)
    ast = parse(tokens)
    program = Compiler().compile_program(ast)
    write_program(out_path, program)
    print(f"source LoC: {len(src.splitlines())} code instr: {len(program.code)} data words: {len(program.data)}")


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Usage: translator.py <input.lisp> <output.bin>"
    _, source_path, target_path = sys.argv
    main(source_path, target_path)
