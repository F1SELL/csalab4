"""Microcode ROM: control words, decoder table, and human-readable descriptions.

Runtime loads this module (not JSON dicts). Pattern follows course microcode examples:
MROM[] + MROM_DESC[] + DECODER[opcode].
"""

from __future__ import annotations

from enum import IntEnum

from isa import Opcode

MROM_SIZE = 128


class Cond(IntEnum):
    ALWAYS = 0b001
    DECODE = 0b111


class Action(IntEnum):
    FETCH_IR = 1
    DISPATCH = 2
    EXEC_SEM = 3


def encode_signals(
    action: Action,
    cond: Cond = Cond.ALWAYS,
    next_addr: int = 0,
    halted: int = 0,
) -> int:
    return (
        (halted & 1) << 31
        | (int(action) & 0xFF) << 16
        | (int(cond) & 0x7) << 6
        | (next_addr & 0x3F)
    )


def decode_action(control_word: int) -> Action:
    return Action((control_word >> 16) & 0xFF)


def decode_cond(control_word: int) -> Cond:
    return Cond((control_word >> 6) & 0x7)


def decode_next_addr(control_word: int) -> int:
    return control_word & 0x3F


def is_halted(control_word: int) -> bool:
    return bool((control_word >> 31) & 1)


MROM: list[int] = [0] * MROM_SIZE
MROM_DESC: list[str] = [""] * MROM_SIZE
DECODER: list[int] = [0] * 256
MROM_LABEL: list[str] = ["FETCH"] * MROM_SIZE

# FETCH: exactly 2 microinstructions
MROM[0] = encode_signals(Action.FETCH_IR, Cond.ALWAYS, next_addr=1)
MROM_DESC[0] = "IR <- Mem[PC]"

MROM[1] = encode_signals(Action.DISPATCH, Cond.DECODE)
MROM_DESC[1] = "uPC <- DECODER[IR.opcode]"

_exec_addr = 2
for op in Opcode:
    DECODER[int(op)] = _exec_addr
    MROM[_exec_addr] = encode_signals(Action.EXEC_SEM, Cond.ALWAYS, next_addr=0)
    MROM_DESC[_exec_addr] = f"EXEC {op.name}; -> FETCH"
    MROM_LABEL[_exec_addr] = op.name
    _exec_addr += 1

FETCH_MICRO_STEPS = 2
