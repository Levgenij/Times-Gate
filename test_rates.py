import unittest

from rates import parse


class ParseTest(unittest.TestCase):
    def test_picks_bank_rates(self):
        data = {"exchangeRate": [
            {"currency": "EUR", "saleRateNB": 51.05, "purchaseRateNB": 51.05, "saleRate": 51.7, "purchaseRate": 50.7},
            {"currency": "USD", "saleRateNB": 45.66, "purchaseRateNB": 45.66, "saleRate": 46.1, "purchaseRate": 45.5},
            {"currency": "NOK", "saleRateNB": 4.94, "purchaseRateNB": 4.94},
        ]}
        self.assertEqual(parse(data), {"USD": (45.5, 46.1), "EUR": (50.7, 51.7)})

    def test_not_published_yet(self):
        self.assertIsNone(parse({"exchangeRate": []}))
        # only NBU rate, no bank rate for USD
        self.assertIsNone(parse({"exchangeRate": [
            {"currency": "USD", "saleRateNB": 45.66, "purchaseRateNB": 45.66},
            {"currency": "EUR", "saleRate": 51.7, "purchaseRate": 50.7}]}))


if __name__ == "__main__":
    unittest.main()
