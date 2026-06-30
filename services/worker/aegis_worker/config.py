import os
from pathlib import Path

from aegis_worker.portfolio_config import resolve_symbols

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def load_env_file(env_path: Path, override: bool = False) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_env_file(PROJECT_ROOT / ".env")
ACTIVE_TRADING_ENV = os.getenv("AEGIS_TRADING_ENV", "main").lower()
if ACTIVE_TRADING_ENV == "live_life":
    load_env_file(PROJECT_ROOT / ".env.live-life", override=True)


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    trading_environment: str = ACTIVE_TRADING_ENV
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_reasoning_model: str = os.getenv("OPENAI_REASONING_MODEL", "gpt-4.1")
    exness_demo_login: str | None = os.getenv("EXNESS_DEMO_LOGIN")
    exness_demo_password: str | None = os.getenv("EXNESS_DEMO_PASSWORD")
    exness_demo_server: str | None = os.getenv("EXNESS_DEMO_SERVER")
    mt5_terminal_path: str | None = os.getenv("MT5_TERMINAL_PATH")
    mt5_account_id: str = os.getenv("MT5_ACCOUNT_ID", "primary")
    auto_trade_enabled: bool = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    trading_profile: str = os.getenv("TRADING_PROFILE", "guarded").lower()
    worker_poll_seconds: int = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    max_open_trades: int = int(os.getenv("MAX_OPEN_TRADES", "1"))
    max_daily_trades: int = int(os.getenv("MAX_DAILY_TRADES", "100"))
    max_risk_per_trade_usd: float = float(os.getenv("MAX_RISK_PER_TRADE_USD", "0.50"))
    target_profit_per_trade_usd: float = float(os.getenv("TARGET_PROFIT_PER_TRADE_USD", "0.75"))
    max_daily_loss_usd: float = float(os.getenv("MAX_DAILY_LOSS_USD", "2.00"))
    minimum_risk_reward: float = float(os.getenv("MINIMUM_RISK_REWARD", "1.50"))
    trade_cooldown_seconds: int = int(os.getenv("TRADE_COOLDOWN_SECONDS", "300"))
    auto_scan_interval_seconds: int = int(os.getenv("AUTO_SCAN_INTERVAL_SECONDS", "300"))
    news_refresh_seconds: int = int(os.getenv("NEWS_REFRESH_SECONDS", "900"))
    ai_review_required: bool = os.getenv("AI_REVIEW_REQUIRED", "true").lower() == "true"
    trading_portfolios: list[str] = parse_csv(os.getenv("TRADING_PORTFOLIOS", ""))
    trading_symbols: list[str] = resolve_symbols(
        trading_portfolios,
        parse_csv(os.getenv("TRADING_SYMBOLS", "XAUUSDm,EURUSDm,BTCUSDm"))
    )


settings = Settings()
