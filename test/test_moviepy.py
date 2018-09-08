# pylint: disable=missing-docstring
import unittest

import pypopquiz as ppq
import pypopquiz.backends.moviepy

class TestMoviepy(unittest.TestCase):
    def test_get_scaled_size(self) -> None:
        mpy = ppq.backends.moviepy.Moviepy
        self.assertEqual(mpy.get_scaled_size(800, 600, 400, 300), (400, 300))
        self.assertEqual(mpy.get_scaled_size(800, 600, 1200, 300), (400, 300))
        self.assertEqual(mpy.get_scaled_size(800, 600, 800, 1200), (800, 600))
        self.assertEqual(mpy.get_scaled_size(800, 600, 800, 300), (400, 300))
        self.assertEqual(mpy.get_scaled_size(400, 300, 800, 700), (800, 600))
        self.assertEqual(mpy.get_scaled_size(800, 600, 200, 75), (100, 75))
