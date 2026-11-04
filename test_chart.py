import unittest

from chart import BOTTOM, LEFT, RIGHT, TOP, points


class PointsTest(unittest.TestCase):
    def test_scales_into_chart_area(self):
        pts = points([10, 30, 20])
        self.assertEqual(pts[0], (LEFT, BOTTOM))   # min at the bottom-left
        self.assertEqual(pts[1][1], TOP)           # max at the top
        self.assertEqual(pts[-1][0], RIGHT)        # last point at the right edge

    def test_flat_series(self):
        self.assertTrue(all(y == BOTTOM for _, y in points([5, 5, 5])))


if __name__ == "__main__":
    unittest.main()
