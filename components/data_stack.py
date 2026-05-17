"""ACC/SHADOW helper for lab4 machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from components.memory import Memory

if TYPE_CHECKING:
    from data_path import CPUState


@dataclass
class DataStack:
    state: CPUState
    memory: Memory
    acc_tag: int | None = None
    shadow_tag: int | None = None
    shadow_dirty: bool = False

    def read_addr_value(self, addr: int) -> int:
        if self.acc_tag == addr:
            return self.state.acc
        if self.shadow_dirty and self.shadow_tag == addr:
            return self.state.shadow
        return self.memory.load(addr)

    def flush_shadow(self) -> int | None:
        if self.shadow_dirty and self.shadow_tag is not None:
            tag = self.shadow_tag
            self.memory.store(tag, self.state.shadow)
            self.shadow_tag = None
            self.shadow_dirty = False
            return tag
        self.shadow_tag = None
        self.shadow_dirty = False
        return None
