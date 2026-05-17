"""Microcoded control unit for lab4 machine."""

from __future__ import annotations

import os

from components.alu import ALU
from components.call_stack import CallStack
from components.io import StreamIO
from data_path import DataPath
from isa import Instruction, Opcode, pack_word
from microcode.micro_rom import (
    DECODER,
    MROM,
    MROM_DESC,
    Action,
    Cond,
    decode_action,
    decode_cond,
    decode_next_addr,
)

PORT_IN = 0
PORT_OUT = 1


class Machine:
    def __init__(
        self,
        code: list[Instruction],
        data: list[int],
        input_buffer: list[str],
        superscalar_enabled: bool | None = None,
    ):
        self.code = code
        self.dp = DataPath(data)
        self.data = self.dp.data
        self.state = self.dp.state
        self.alu = ALU()
        self.io = StreamIO(input_buffer)
        self.halted = False
        self.log: list[str] = []
        self.call_stack = CallStack()
        self.current_instr: Instruction | None = None
        self.u_pc: int = 0
        if superscalar_enabled is None:
            env = os.getenv("SUPERSCALAR", "1")
            self.superscalar_enabled = env != "0"
        else:
            self.superscalar_enabled = superscalar_enabled

    def tick(self, msg: str) -> None:
        self.log.append(msg)
        self.state.tick += 1

    def flush_shadow(self) -> None:
        tag = self.dp.flush_shadow()
        if tag is not None:
            self.tick(f"SUPER flush shadow -> [{tag}]")

    def exec_semantic(self, instr: Instruction) -> None:
        """Machine instruction semantics (no extra ticks; one micro-step = one tick in step())."""
        op = instr.opcode
        arg = instr.arg
        s = self.state
        dp = self.dp
        if op == Opcode.NOP:
            s.pc += 1
        elif op == Opcode.HALT:
            self.halted = True
        elif op == Opcode.LOADI:
            s.acc = pack_word(arg)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.LOAD:
            if dp.acc_tag == arg:
                pass
            elif dp.shadow_dirty and dp.shadow_tag == arg:
                s.acc = s.shadow
                dp.acc_tag = arg
            else:
                s.acc = dp.load_mem(arg)
                dp.acc_tag = arg
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.STORE:
            if dp.shadow_tag is None:
                s.acc, s.shadow = s.shadow, s.acc
                dp.acc_tag, dp.shadow_tag = dp.shadow_tag, arg
                dp.shadow_dirty = True
            elif dp.shadow_tag == arg:
                s.shadow = s.acc
                dp.shadow_dirty = True
            else:
                dp.store_mem(dp.shadow_tag, s.shadow)
                dp.store_mem(arg, s.acc)
                dp.acc_tag = arg
                dp.shadow_tag = None
                dp.shadow_dirty = False
            s.pc += 1
        elif op == Opcode.ADD:
            val = dp.read_addr_value(arg)
            s.acc = self.alu.add(s.acc, val)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.SUB:
            val = dp.read_addr_value(arg)
            s.acc = self.alu.sub(s.acc, val)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.MUL:
            val = dp.read_addr_value(arg)
            s.acc = self.alu.mul(s.acc, val)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.DIV:
            val = dp.read_addr_value(arg)
            s.acc = self.alu.div(s.acc, val)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.MOD:
            val = dp.read_addr_value(arg)
            s.acc = self.alu.mod(s.acc, val)
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.CMP:
            right = dp.read_addr_value(arg)
            dp.set_cmp_flags(s.acc, right)
            s.acc = 1 if s.flag_z else 0
            dp.acc_tag = None
            s.pc += 1
        elif op == Opcode.JMP:
            s.pc = arg
        elif op == Opcode.JZ:
            s.pc = arg if s.acc == 0 else s.pc + 1
        elif op == Opcode.JNZ:
            s.pc = arg if s.acc != 0 else s.pc + 1
        elif op == Opcode.JL:
            s.pc = arg if s.flag_l else s.pc + 1
        elif op == Opcode.JG:
            s.pc = arg if s.flag_g else s.pc + 1
        elif op == Opcode.IN:
            if arg != PORT_IN:
                raise EOFError("Input buffer is empty")
            ch = self.io.read_char()
            s.acc = ord(ch)
            dp.acc_tag = None
            s.pc += 1
        elif op == Opcode.OUT:
            if arg == PORT_OUT:
                self.io.write_char(chr(s.acc & 0xFF))
            s.pc += 1
        elif op == Opcode.SWAP:
            s.acc, s.shadow = s.shadow, s.acc
            dp.acc_tag, dp.shadow_tag = dp.shadow_tag, dp.acc_tag
            s.pc += 1
        elif op == Opcode.STORE_SHADOW:
            dp.store_mem(arg, s.shadow)
            if dp.shadow_tag == arg:
                dp.shadow_dirty = False
            s.pc += 1
        elif op == Opcode.PUSH:
            self.call_stack.push_value(s.acc)
            s.pc += 1
        elif op == Opcode.POP:
            if not self.call_stack.frames:
                dp.store_mem(arg, 0)
                s.acc = 0
            else:
                v = self.call_stack.pop_value()
                dp.store_mem(arg, v)
                s.acc = v
            dp.acc_tag = arg
            s.pc += 1
        elif op == Opcode.CALL:
            argc = self.call_stack.pop_value()
            args = self.call_stack.pop_values(argc)
            self.call_stack.push_call(s.pc + 1, args)
            s.pc = arg
        elif op == Opcode.RET:
            ret_pc = self.call_stack.pop_return_pc()
            if ret_pc is None or ret_pc < 0:
                self.halted = True
            else:
                s.pc = ret_pc
        elif op == Opcode.LOAD_LOCAL:
            locals_ = self.call_stack.peek_locals()
            if locals_ is not None and 0 <= arg < len(locals_):
                s.acc = locals_[arg]
            else:
                s.acc = 0
            dp.acc_tag = None
            s.flag_z = s.acc == 0
            s.pc += 1
        elif op == Opcode.STORE_LOCAL:
            self.call_stack.store_local(arg, s.acc)
            s.pc += 1
        else:
            s.pc += 1

    def try_superscalar_pair(self) -> bool:
        if self.state.pc + 1 >= len(self.code):
            return False
        i1 = self.code[self.state.pc]
        i2 = self.code[self.state.pc + 1]
        if not self._is_issue_compatible(i1, i2):
            return False
        hazard = self._hazard_reason(i1, i2)
        if hazard:
            self.tick(f"SUPER stall {i1.opcode.name}+{i2.opcode.name}: {hazard}")
            return False
        self.tick(f"SUPER issue2 {i1.opcode.name}+{i2.opcode.name}")
        self.exec_semantic(i1)
        self.exec_semantic(i2)
        self.tick(f"SUPER commit2 pc={self.state.pc}")
        self.current_instr = None
        self.u_pc = 0
        return True

    def _issue_unit(self, instr: Instruction) -> str:
        if instr.opcode in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD, Opcode.CMP}:
            return "ALU"
        if instr.opcode in {Opcode.STORE, Opcode.STORE_SHADOW, Opcode.LOAD, Opcode.LOADI, Opcode.IN, Opcode.OUT}:
            return "MEMIO"
        return "CTRL"

    def _is_issue_compatible(self, i1: Instruction, i2: Instruction) -> bool:
        return self._issue_unit(i1) == "ALU" and self._issue_unit(i2) == "MEMIO"

    def _read_set(self, instr: Instruction) -> set[str]:
        op = instr.opcode
        if op in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD, Opcode.CMP}:
            return {"ACC", f"MEM[{instr.arg}]"}
        if op == Opcode.STORE:
            return {"ACC", "SHADOW"}
        if op == Opcode.STORE_SHADOW:
            return {"SHADOW"}
        if op == Opcode.LOAD:
            return {f"MEM[{instr.arg}]"}
        if op == Opcode.OUT:
            return {"ACC"}
        return set()

    def _write_set(self, instr: Instruction) -> set[str]:
        op = instr.opcode
        if op in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.MOD}:
            return {"ACC", "FLAG_Z"}
        if op == Opcode.CMP:
            return {"ACC", "FLAG_Z", "FLAG_L", "FLAG_G"}
        if op in {Opcode.LOAD, Opcode.LOADI, Opcode.IN}:
            return {"ACC", "FLAG_Z"}
        if op == Opcode.SWAP:
            return {"ACC", "SHADOW"}
        if op == Opcode.STORE:
            return {"SHADOW", f"MEM[{instr.arg}]"}
        if op == Opcode.STORE_SHADOW:
            return {f"MEM[{instr.arg}]"}
        return set()

    def _hazard_reason(self, i1: Instruction, i2: Instruction) -> str | None:
        r1, w1 = self._read_set(i1), self._write_set(i1)
        r2, w2 = self._read_set(i2), self._write_set(i2)
        raw = w1 & r2
        war = r1 & w2
        waw = w1 & w2
        if raw:
            return f"RAW {sorted(raw)}"
        if war:
            return f"WAR {sorted(war)}"
        if waw:
            return f"WAW {sorted(waw)}"
        return None

    def apply_control_word(self, control_word: int) -> None:
        action = decode_action(control_word)
        if action == Action.FETCH_IR:
            self.current_instr = self.code[self.state.pc]
            self.u_pc = decode_next_addr(control_word)
        elif action == Action.DISPATCH:
            assert self.current_instr is not None
            if decode_cond(control_word) == Cond.DECODE:
                self.u_pc = DECODER[int(self.current_instr.opcode)]
            else:
                self.u_pc = decode_next_addr(control_word)
        elif action == Action.EXEC_SEM:
            assert self.current_instr is not None
            self.exec_semantic(self.current_instr)
            self.current_instr = None
            self.u_pc = decode_next_addr(control_word)

    def step(self) -> None:
        if self.halted:
            return
        if self.u_pc == 0 and self.superscalar_enabled and self.try_superscalar_pair():
            return

        control_word = MROM[self.u_pc]
        self.tick(f"uPC={self.u_pc} {MROM_DESC[self.u_pc]}")
        self.apply_control_word(control_word)

    def run(self, limit: int = 200000):
        try:
            while not self.halted and self.state.tick < limit:
                self.step()
        except EOFError:
            self.halted = True
            self.tick("stop: input exhausted")
        self.flush_shadow()
        if self.state.tick >= limit:
            raise RuntimeError("Simulation limit exceeded")
        return self.io.output(), self.log
