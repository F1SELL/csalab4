"""Stream I/O component for port-mapped machine."""

from __future__ import annotations


class StreamIO:
    def __init__(self, input_buffer: list[str]):
        self.input_buffer = list(input_buffer)
        self.output_buffer: list[str] = []

    def read_char(self) -> str:
        if not self.input_buffer:
            raise EOFError("Input buffer is empty")
        return self.input_buffer.pop(0)

    def write_char(self, ch: str) -> None:
        self.output_buffer.append(ch)

    def output(self) -> str:
        return "".join(self.output_buffer)

