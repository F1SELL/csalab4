"""ALU helper for lab4 machine."""

from __future__ import annotations

from isa import pack_word


class ALU:
    @staticmethod
    def add(left: int, right: int) -> int:
        return pack_word(left + right)

    @staticmethod
    def sub(left: int, right: int) -> int:
        return pack_word(left - right)

    @staticmethod
    def mul(left: int, right: int) -> int:
        return pack_word(left * right)

    @staticmethod
    def div(left: int, right: int) -> int:
        if right == 0:
            return 0
        return pack_word(int(left / right))

    @staticmethod
    def mod(left: int, right: int) -> int:
        if right == 0:
            return 0
        return pack_word(left % right)

