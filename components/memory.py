"""Unified memory component for lab4 machine."""

from __future__ import annotations

from isa import pack_word


class Memory:
    def __init__(self, data: list[int]):
        self.data = [pack_word(x) for x in data]

    def load(self, addr: int) -> int:
        return self.data[addr]

    def store(self, addr: int, value: int) -> None:
        self.data[addr] = pack_word(value)

