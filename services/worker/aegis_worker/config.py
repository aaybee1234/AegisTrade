import os
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def load_env_file() -> None:
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_reasoning_model: str = os.getenv("OPENAI_REASONING_MODEL", "gpt-4.1")
    exness_demo_login: str | None = os.getenv("EXNESS_DEMO_LOGIN")
    exness_demo_password: str | None = os.getenv("EXNESS_DEMO_PASSWORD")
    exness_demo_server: str | None = os.getenv("EXNESS_DEMO_SERVER")
    mt5_terminal_path: str | None = os.getenv("MT5_TERMINAL_PATH")
    mt5_account_id: str = os.getenv("MT5_ACCOUNT_ID", "primary")
    auto_trade_enabled: bool = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    worker_poll_seconds: int = int(os.getenv("WORKER_POLL_SECONDS", "60"))
    max_open_trades: int = int(os.getenv("MAX_OPEN_TRADES", "2"))
    max_daily_trades: int = int(os.getenv("MAX_DAILY_TRADES", "100"))
    max_risk_per_trade_usd: float = float(os.getenv("MAX_RISK_PER_TRADE_USD", "10"))
    target_profit_per_trade_usd: float = float(os.getenv("TARGET_PROFIT_PER_TRADE_USD", "0.50"))


settings = Settings()
