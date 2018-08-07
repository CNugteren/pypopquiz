# pylint: disable=missing-docstring
import unittest

import pypopquiz as ppq
import pypopquiz.video


class TestIO(unittest.TestCase):

    def test_get_interval_in_s(self) -> None:
        self.assertEqual(ppq.video.get_interval_in_s(["0:10", "1:11"]), [10, 71])
        self.assertEqual(ppq.video.get_interval_in_s(["2:10", "4:09"]), [130, 249])
        self.assertEqual(ppq.video.get_interval_in_s(["1:10", "1:11"]), [70, 71])
