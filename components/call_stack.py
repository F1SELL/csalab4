"""Call stack component for lab4 machine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CallStackFrame:
	return_pc: int
	values: list[int] = field(default_factory=list)


class CallStack:
	def __init__(self) -> None:
		self.frames: list[CallStackFrame] = []

	def push_value(self, value: int) -> None:
		self.frames.append(CallStackFrame(-1, [value]))

	def pop_value(self) -> int:
		if not self.frames:
			return 0
		frame = self.frames.pop()
		return frame.values[0] if frame.values else 0

	def pop_values(self, count: int) -> list[int]:
		values = [self.pop_value() for _ in range(max(0, count))]
		values.reverse()
		return values

	def push_call(self, return_pc: int, args: list[int]) -> None:
		self.frames.append(CallStackFrame(return_pc, list(args)))

	def pop_return_pc(self) -> int | None:
		if not self.frames:
			return None
		return self.frames.pop().return_pc

	def peek_locals(self) -> list[int] | None:
		if not self.frames:
			return None
		return self.frames[-1].values

	def store_local(self, index: int, value: int) -> None:
		if not self.frames:
			return
		frame = self.frames[-1]
		while len(frame.values) <= index:
			frame.values.append(0)
		frame.values[index] = value


