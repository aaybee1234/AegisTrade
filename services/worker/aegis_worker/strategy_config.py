from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolStrategyConfig:
    symbol: str
    lot_size: float
    max_spread_points: int
    min_stop_points: int
    max_stop_points: int
    risk_reward: float
    atr_multiplier: float


DEFAULT_CONFIG = SymbolStrategyConfig(
    symbol="DEFAULT",
    lot_size=0.01,
    max_spread_points=50,
    min_stop_points=200,
    max_stop_points=2000,
    risk_reward=2.0,
    atr_multiplier=1.8
)

SYMBOL_CONFIGS = {
    "EURUSDm": SymbolStrategyConfig(
        symbol="EURUSDm",
        lot_size=0.01,
        max_spread_points=35,
        min_stop_points=200,
        max_stop_points=1200,
        risk_reward=2.0,
        atr_multiplier=1.8
    ),
    "XAUUSDm": SymbolStrategyConfig(
        symbol="XAUUSDm",
        lot_size=0.01,
        max_spread_points=250,
        min_stop_points=1200,
        max_stop_points=8000,
        risk_reward=1.8,
        atr_multiplier=2.0
    ),
    "BTCUSDm": SymbolStrategyConfig(
        symbol="BTCUSDm",
        lot_size=0.01,
        max_spread_points=1500,
        min_stop_points=12000,
        max_stop_points=50000,
        risk_reward=1.6,
        atr_multiplier=2.2
    ),
    "ETHUSDm": SymbolStrategyConfig(
        symbol="ETHUSDm", lot_size=0.01, max_spread_points=1200,
        min_stop_points=8000, max_stop_points=40000, risk_reward=1.6, atr_multiplier=2.2
    ),
    "GBPUSDm": SymbolStrategyConfig(
        symbol="GBPUSDm", lot_size=0.01, max_spread_points=45,
        min_stop_points=250, max_stop_points=1400, risk_reward=2.0, atr_multiplier=1.8
    ),
    "USDJPYm": SymbolStrategyConfig(
        symbol="USDJPYm", lot_size=0.01, max_spread_points=45,
        min_stop_points=250, max_stop_points=1400, risk_reward=2.0, atr_multiplier=1.8
    ),
    "AUDUSDm": SymbolStrategyConfig(
        symbol="AUDUSDm", lot_size=0.01, max_spread_points=45,
        min_stop_points=250, max_stop_points=1400, risk_reward=2.0, atr_multiplier=1.8
    ),
    "USDCADm": SymbolStrategyConfig(
        symbol="USDCADm", lot_size=0.01, max_spread_points=45,
        min_stop_points=250, max_stop_points=1400, risk_reward=2.0, atr_multiplier=1.8
    )
}


def config_for_symbol(symbol: str) -> SymbolStrategyConfig:
    return SYMBOL_CONFIGS.get(symbol, DEFAULT_CONFIG)
