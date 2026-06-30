from collections.abc import Iterable


PORTFOLIOS: dict[str, tuple[str, ...]] = {
    "metals": ("XAUUSDm", "XAGUSDm", "XPTUSDm", "XPDUSDm"),
    "energy": ("USOILm", "UKOILm"),
    "crypto": ("BTCUSDm", "ETHUSDm", "BTCUSDTm", "ETHBTCm"),
    "forex": ("EURUSDm", "GBPUSDm", "USDJPYm", "AUDUSDm", "USDCADm"),
}


def resolve_symbols(portfolios: Iterable[str], explicit_symbols: Iterable[str]) -> list[str]:
    resolved: list[str] = []
    for portfolio in portfolios:
        resolved.extend(PORTFOLIOS.get(portfolio.lower(), ()))
    resolved.extend(explicit_symbols)
    return list(dict.fromkeys(resolved))


def portfolio_for_symbol(symbol: str) -> str:
    for name, symbols in PORTFOLIOS.items():
        if symbol in symbols:
            return name
    return "custom"
