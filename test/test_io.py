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

    def test_get_interval_in_s(self) -> None:
        self.assertEqual(ppq.io.get_interval_in_s(("0:10", "1:11")), (10, 71))
        self.assertEqual(ppq.io.get_interval_in_s(("2:10", "4:09")), (130, 249))
        self.assertEqual(ppq.io.get_interval_in_s(("1:10", "1:11")), (70, 71))

    def test_get_interval_duration(self) -> None:
        self.assertEqual(ppq.io.get_interval_duration(("0:10", "1:11")), 71 - 10)
        self.assertEqual(ppq.io.get_interval_duration(("2:10", "4:09")), 249 - 130)
        self.assertEqual(ppq.io.get_interval_duration(("1:10", "1:11")), 71 - 70)
