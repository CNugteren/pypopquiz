# pylint: disable=missing-docstring
import unittest
from pathlib import Path

import pypopquiz as ppq
import pypopquiz.io


class TestIO(unittest.TestCase):

    SAMPLE_FILES = [Path("samples/round01.json")]

    def test_read_input(self) -> None:
        for sample_file in self.SAMPLE_FILES:
            result = ppq.io.read_input(sample_file)
            self.assertTrue("round" in result.keys())

    def test_verify_input(self) -> None:
        for sample_file in self.SAMPLE_FILES:
            result = ppq.io.read_input(sample_file)
            ppq.io.verify_input(result)  # should not raise an assert
