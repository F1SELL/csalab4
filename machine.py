#!/usr/bin/env python3
"""Entry point for lab4 machine."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, cast

from control_unit import Machine
from isa import from_bytes


def load_data(path: str) -> list[int]:
    with open(path, encoding="utf-8") as f:
        payload = cast(dict[str, Any], json.load(f))
    return cast(list[int], payload["data"])


def main(code_path: str, input_path: str, log_file: str | None = None, verbose: bool = False) -> None:
    with open(code_path, "rb") as f:
        code = from_bytes(f.read())
    data = load_data(code_path + ".data.json")
    with open(input_path, encoding="utf-8") as f:
        input_tokens = list(f.read())
    machine = Machine(code, data, input_tokens)
    output, log = machine.run()
    log_text = "\n".join(log) + "\n"
    if log_file:
        Path(log_file).write_text(log_text, encoding="utf-8")
    if verbose:
        for row in log:
            logging.debug(row)
    print(output, end="")
    print(f"\nticks: {machine.state.tick}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lab4 processor simulator")
    parser.add_argument("code_file", help="Binary code file (.bin)")
    parser.add_argument("input_file", help="Input stream file")
    parser.add_argument("--log-file", help="Write full simulation log to this path")
    parser.add_argument("--verbose", action="store_true", help="Print log lines to stderr via logging")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    main(args.code_file, args.input_file, log_file=args.log_file, verbose=args.verbose)
