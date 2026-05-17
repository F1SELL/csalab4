import json
import tempfile
import unittest
from pathlib import Path

from ast_format import format_program_ast
from isa import from_bytes
from machine import Machine
from translator import Compiler, parse, tokenize, write_program

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden"


def _run_case(cfg_path: Path) -> None:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    src_path = ROOT / cfg["source"]
    input_path = ROOT / cfg["input"]

    src = src_path.read_text(encoding="utf-8")
    ast = parse(tokenize(src))
    program = Compiler().compile_program(ast)

    with tempfile.TemporaryDirectory() as td:
        out_bin = Path(td) / f"{cfg['name']}.bin"
        write_program(str(out_bin), program)

        assert out_bin.exists()
        assert Path(str(out_bin) + ".hex").exists()
        assert Path(str(out_bin) + ".data.json").exists()
        assert Path(str(out_bin) + ".ast.json").exists()
        assert Path(str(out_bin) + ".ast.txt").exists()

        code = from_bytes(out_bin.read_bytes())
        data_payload = json.loads(Path(str(out_bin) + ".data.json").read_text(encoding="utf-8"))
        input_tokens = list(input_path.read_text(encoding="utf-8"))

        machine = Machine(code, data_payload["data"], input_tokens)
        output, log = machine.run(limit=500000)

    assert output == cfg["expected_output"]
    assert machine.state.tick == cfg["expected_ticks"]

    log_file = GOLDEN_DIR / cfg["log_file"]
    expected_log = log_file.read_text(encoding="utf-8")
    actual_log = "\n".join(log) + "\n"
    assert actual_log == expected_log, f"log mismatch for {cfg['name']}"

    ast_file = GOLDEN_DIR / cfg["ast_file"]
    expected_ast = ast_file.read_text(encoding="utf-8")
    actual_ast = format_program_ast(ast) + "\n"
    assert actual_ast == expected_ast, f"AST mismatch for {cfg['name']}"

    for needle in cfg.get("required_log_contains", []):
        assert any(needle in row for row in log), f"missing log fragment: {needle}"


class GoldenPipelineTest(unittest.TestCase):
    def test_hello(self):
        _run_case(GOLDEN_DIR / "hello.json")

    def test_cat(self):
        _run_case(GOLDEN_DIR / "cat.json")

    def test_hello_user_name(self):
        _run_case(GOLDEN_DIR / "hello_user_name.json")

    def test_sort(self):
        _run_case(GOLDEN_DIR / "sort.json")

    def test_double_precision(self):
        _run_case(GOLDEN_DIR / "double_precision.json")

    def test_prob1(self):
        _run_case(GOLDEN_DIR / "prob1.json")

    def test_fact_recursion(self):
        _run_case(GOLDEN_DIR / "fact.json")


if __name__ == "__main__":
    unittest.main()
