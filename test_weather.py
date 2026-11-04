import unittest

from weather import describe


class DescribeTest(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(describe(0), "Clear")
        self.assertEqual(describe(3), "Overcast")
        self.assertEqual(describe(63), "Rain")
        self.assertEqual(describe(99), "Thunderstorm")
        self.assertEqual(describe(42), "")  # unknown code: no label rather than a crash


if __name__ == "__main__":
    unittest.main()
