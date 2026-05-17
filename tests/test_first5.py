import json
import tempfile
import unittest
from pathlib import Path

from ast_format import format_program_ast
from isa import Instruction, Opcode, from_bytes
from machine import Machine
from translator import Compiler, parse, tokenize, write_program


class FirstFiveCoverageTest(unittest.TestCase):
    def test_lisp_aliases_and_ast_artifact(self):
        src = """
        (defun sum3 (a b c)
          (setq t (+ a b c))
          t)
        (setq x 0)
        (loop (< x 3)
          (setq x (+ x 1)))
        (out 1 (sum3 x 2 3))
        """
        ast = parse(tokenize(src))
        program = Compiler().compile_program(ast)

        with tempfile.TemporaryDirectory() as td:
            out_bin = Path(td) / "prog.bin"
            write_program(str(out_bin), program)
            ast_txt = Path(str(out_bin) + ".ast.txt")
            self.assertTrue(ast_txt.exists())
            text = ast_txt.read_text(encoding="utf-8")
            self.assertIn("defun", text)
            self.assertIn("loop", text)
            self.assertEqual(text, format_program_ast(ast) + "\n")

    def test_microcode_trace_fetch_two_steps(self):
        code = [Instruction(Opcode.LOADI, 65), Instruction(Opcode.OUT, 1), Instruction(Opcode.HALT, 0)]
        machine = Machine(code, data=[0, 0], input_buffer=[])
        out, log = machine.run(limit=1000)
        self.assertEqual(out, "A")
        self.assertEqual(log[0], "uPC=0 IR <- Mem[PC]")
        self.assertEqual(log[1], "uPC=1 uPC <- DECODER[IR.opcode]")
        self.assertTrue(any("EXEC LOADI" in row for row in log))
        self.assertTrue(any("EXEC OUT" in row for row in log))

    def test_superscalar_issue_and_stall(self):
        issue_code = [
            Instruction(Opcode.LOADI, 1),
            Instruction(Opcode.STORE, 0),
            Instruction(Opcode.LOAD, 0),
            Instruction(Opcode.ADD, 0),
            Instruction(Opcode.STORE_SHADOW, 1),
            Instruction(Opcode.HALT, 0),
        ]
        m1 = Machine(issue_code, data=[0, 0], input_buffer=[], superscalar_enabled=True)
        _, log1 = m1.run(limit=2000)
        self.assertTrue(any("SUPER issue2" in row for row in log1))

        stall_code = [
            Instruction(Opcode.LOADI, 1),
            Instruction(Opcode.STORE, 0),
            Instruction(Opcode.LOAD, 0),
            Instruction(Opcode.ADD, 0),
            Instruction(Opcode.STORE, 1),
            Instruction(Opcode.HALT, 0),
        ]
        m2 = Machine(stall_code, data=[0, 0], input_buffer=[], superscalar_enabled=True)
        _, log2 = m2.run(limit=2000)
        self.assertTrue(any("SUPER stall" in row for row in log2))

    def test_print_setq_expression(self):
        src = "(print (setq x (+ 48 5)))"
        ast = parse(tokenize(src))
        program = Compiler().compile_program(ast)
        with tempfile.TemporaryDirectory() as td:
            out_bin = Path(td) / "ps.bin"
            write_program(str(out_bin), program)
            code = from_bytes(out_bin.read_bytes())
            data_payload = json.loads(Path(str(out_bin) + ".data.json").read_text(encoding="utf-8"))
            machine = Machine(code, data_payload["data"], [])
            output, _ = machine.run(limit=5000)
        self.assertEqual(output, "5")

    def test_superscalar_fewer_ticks_than_scalar(self):
        issue_code = [
            Instruction(Opcode.LOADI, 1),
            Instruction(Opcode.STORE, 0),
            Instruction(Opcode.LOAD, 0),
            Instruction(Opcode.ADD, 0),
            Instruction(Opcode.STORE_SHADOW, 1),
            Instruction(Opcode.HALT, 0),
        ]
        m_ss = Machine(issue_code, data=[0, 0], input_buffer=[], superscalar_enabled=True)
        out_ss, _ = m_ss.run(limit=2000)
        m_sc = Machine(issue_code, data=[0, 0], input_buffer=[], superscalar_enabled=False)
        out_sc, _ = m_sc.run(limit=2000)
        self.assertEqual(out_ss, out_sc)
        self.assertLess(m_ss.state.tick, m_sc.state.tick)


if __name__ == "__main__":
    unittest.main()
