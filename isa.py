"""ISA and binary encoding for lab4 processor."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

WORD_BITS = 32
WORD_MASK = (1 << WORD_BITS) - 1


class Opcode(IntEnum):
    NOP = 0x00
    HALT = 0x01
    LOADI = 0x02
    LOAD = 0x03
    STORE = 0x04
    ADD = 0x05
    SUB = 0x06
    MUL = 0x07
    DIV = 0x08
    MOD = 0x09
    CMP = 0x0A
    JMP = 0x0B
    JZ = 0x0C
    JNZ = 0x0D
    JL = 0x0E
    JG = 0x0F
    IN = 0x10
    OUT = 0x11
    SWAP = 0x12
    STORE_SHADOW = 0x13
    CALL = 0x14
    RET = 0x15
    PUSH = 0x16
    POP = 0x17
    LOAD_LOCAL = 0x18
    STORE_LOCAL = 0x19


MNEMONIC_TO_OPCODE = {op.name.lower(): op for op in Opcode}


@dataclass(slots=True)
class Instruction:
    opcode: Opcode
    arg: int = 0


def pack_word(value: int) -> int:
    value &= WORD_MASK
    if value >= (1 << (WORD_BITS - 1)):
        value -= 1 << WORD_BITS
    return value


def encode_instruction(instr: Instruction) -> bytes:
    raw = ((int(instr.opcode) & 0xFF) << 24) | (instr.arg & 0x00FFFFFF)
    return raw.to_bytes(4, "big", signed=False)


def decode_instruction(data: bytes) -> Instruction:
    raw = int.from_bytes(data, "big", signed=False)
    opcode = Opcode((raw >> 24) & 0xFF)
    arg = raw & 0x00FFFFFF
    if arg & 0x00800000:
        arg -= 0x01000000
    return Instruction(opcode, arg)


def to_bytes(code: list[Instruction]) -> bytes:
    buf = bytearray()
    for instr in code:
        buf.extend(encode_instruction(instr))
    return bytes(buf)


def from_bytes(binary: bytes) -> list[Instruction]:
    assert len(binary) % 4 == 0, "Invalid binary length"
    code: list[Instruction] = []
    for i in range(0, len(binary), 4):
        code.append(decode_instruction(binary[i : i + 4]))
    return code


def to_hex_listing(code: list[Instruction]) -> str:
    lines: list[str] = []
    for idx, instr in enumerate(code):
        raw = int.from_bytes(encode_instruction(instr), "big")
        mnemonic = instr.opcode.name.lower()
        if instr.arg:
            mnemonic = f"{mnemonic} {instr.arg}"
        lines.append(f"{idx} - {raw:08X} - {mnemonic}")
    return "\n".join(lines)
