import unittest

from aegis_worker.portfolio_config import portfolio_for_symbol, resolve_symbols


class PortfolioConfigTests(unittest.TestCase):
    def test_resolve_symbols_keeps_portfolios_and_explicit_unique(self) -> None:
        symbols = resolve_symbols(["crypto", "energy"], ["BTCUSDm", "EURUSDm"])

        self.assertIn("BTCUSDm", symbols)
        self.assertIn("ETHUSDm", symbols)
        self.assertIn("USOILm", symbols)
        self.assertIn("EURUSDm", symbols)
        self.assertEqual(symbols.count("BTCUSDm"), 1)

    def test_symbol_portfolio_lookup(self) -> None:
        self.assertEqual(portfolio_for_symbol("XAGUSDm"), "metals")
        self.assertEqual(portfolio_for_symbol("USOILm"), "energy")
        self.assertEqual(portfolio_for_symbol("ETHBTCm"), "crypto")
        self.assertEqual(portfolio_for_symbol("CUSTOMm"), "custom")


if __name__ == "__main__":
    unittest.main()
