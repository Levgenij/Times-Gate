import unittest

from gmail import decide


class DecideTest(unittest.TestCase):
    def test_sequence(self):
        mode, prev = "rates", 0
        expected = [(0, "rates"), (3, "mail"), (3, "mail"), (5, "mail"),
                    (4, "rates"), (4, "rates"), (6, "mail"), (0, "rates")]
        for count, want in expected:
            mode, prev = decide(prev, count, mode), count
            self.assertEqual(mode, want, f"count={count}")


if __name__ == "__main__":
    unittest.main()
