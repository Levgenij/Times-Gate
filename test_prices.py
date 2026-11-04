import unittest

from prices import fmt


class FmtTest(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(fmt(79920), "79,920")
        self.assertEqual(fmt(767.495), "767.50")
        self.assertEqual(fmt(0.03820055), "0.0382")
        self.assertEqual(fmt(0.089983), "0.08998")
        self.assertEqual(fmt(None), "--")


if __name__ == "__main__":
    unittest.main()
