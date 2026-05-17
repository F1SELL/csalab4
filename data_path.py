"""Datapath state and memory operations for lab4 machine."""

from __future__ import annotations

from dataclasses import dataclass

from components.data_stack import DataStack
from components.memory import Memory


@dataclass
class CPUState:
    pc: int = 0
    tick: int = 0
    acc: int = 0
    shadow: int = 0
    flag_z: bool = False
    flag_l: bool = False
    flag_g: bool = False


class DataPath:
    def __init__(self, data: list[int]):
        self.state = CPUState()
        self.memory = Memory(data)
        self.data = self.memory.data
        self.stack = DataStack(self.state, self.memory)

    @property
    def acc_tag(self) -> int | None:
        return self.stack.acc_tag

    @acc_tag.setter
    def acc_tag(self, value: int | None) -> None:
        self.stack.acc_tag = value

    @property
    def shadow_tag(self) -> int | None:
        return self.stack.shadow_tag

    @shadow_tag.setter
    def shadow_tag(self, value: int | None) -> None:
        self.stack.shadow_tag = value

    @property
    def shadow_dirty(self) -> bool:
        return self.stack.shadow_dirty

    @shadow_dirty.setter
    def shadow_dirty(self, value: bool) -> None:
        self.stack.shadow_dirty = value

    def load_mem(self, addr: int) -> int:
        return self.memory.load(addr)

    def store_mem(self, addr: int, value: int) -> None:
        self.memory.store(addr, value)

    def read_addr_value(self, addr: int) -> int:
        # dead-load elimination path: value already in registers
        return self.stack.read_addr_value(addr)

    def flush_shadow(self) -> int | None:
        return self.stack.flush_shadow()

    def set_cmp_flags(self, left: int, right: int) -> None:
        diff = left - right
        self.state.flag_z = diff == 0
        self.state.flag_l = diff < 0
        self.state.flag_g = diff > 0

