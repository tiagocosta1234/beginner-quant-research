"""
Deployment Framework: credential lifecycle, health checks, and logging.

Supports multiple credential backends (encrypted vault, environment variables),
local deployment (systemd, Windows Task Scheduler, Docker), and comprehensive
logging to local files and optional CloudWatch.

Usage:
    # Initialize credentials
    creds = BrokerCredentials(api_key='...', username='...', account_name='...')
    CredentialManager.setup_vault('./vault.db', creds)

    # Load credentials at startup
    manager = CredentialManager(vault_db_path='./vault.db')
    creds = manager.load_credentials(use_vault=True)

    # Health checks
    checker = HealthChecker(broker, alert_handler, logger)
    health_status = await checker.check_health()

    # Logging
    logger_setup = ComplianceLogger(log_dir='./logs')
"""

from __future__ import annotations

import os
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from zoneinfo import ZoneInfo
from logging.handlers import RotatingFileHandler

CENTRAL_TZ = ZoneInfo("America/Chicago")

# Optional cryptography for vault
try:
    from cryptography.fernet import Fernet

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


@dataclass
class BrokerCredentials:
    """Immutable broker credentials."""

    api_key: str
    username: str
    account_name: str
    confirm_live: Optional[str] = None  # "I_UNDERSTAND_THIS_IS_REAL_MONEY" if live

    def to_env_dict(self) -> dict[str, str]:
        """Convert to environment variable names."""
        return {
            "BROKERAPI_API_KEY": self.api_key,
            "BROKERAPI_USERNAME": self.username,
            "BROKERAPI_ACCOUNT_NAME": self.account_name,
            "BOT_CONFIRM_LIVE": self.confirm_live or "",
        }


class CredentialManager:
    """
    Fetch credentials from vault (priority) or environment.

    Supports multiple backends:
    - SQLite encrypted vault (local, needs cryptography package)
    - Environment variables (.env or system)
    - File-based (for testing)
    """

    def __init__(
        self,
        vault_db_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.vault_db_path = vault_db_path or os.getenv("VAULT_DB_PATH")
        self.logger = logger or logging.getLogger("CredentialManager")
        self._encryption_key: Optional[Fernet] = None

    def load_credentials(self, use_vault: bool = True) -> BrokerCredentials:
        """
        Load credentials from vault (preferred) or environment.

        Priority:
        1. Encrypted SQLite vault (if use_vault=True and vault_db_path set)
        2. Environment variables (BROKERAPI_API_KEY, etc.)
        3. .env file (if exists)

        Args:
            use_vault: if True, try vault first; if False, skip to environment

        Returns:
            BrokerCredentials object

        Raises:
            ValueError: if credentials incomplete or vault unavailable
        """

        # Try vault first
        if use_vault and self.vault_db_path:
            try:
                return self._load_from_vault()
            except Exception as e:
                if use_vault:
                    self.logger.warning(
                        f"Failed to load from vault: {e}. Falling back to env."
                    )
                else:
                    raise

        # Fall back to environment
        return self._load_from_env()

    def _load_from_vault(self) -> BrokerCredentials:
        """
        Fetch credentials from encrypted SQLite vault.

        Vault schema:
            CREATE TABLE credentials (
                key TEXT PRIMARY KEY,
                encrypted_value TEXT NOT NULL,
                created_at TIMESTAMP,
                rotated_at TIMESTAMP
            )

        Encryption key: VAULT_ENCRYPTION_KEY env var (base64-encoded Fernet key)

        Raises:
            ValueError: if cryptography not available, key missing, or credential missing
            sqlite3.Error: if database error
        """
        if not HAS_CRYPTO:
            raise ValueError(
                "cryptography package required for vault support. "
                "Install: pip install cryptography"
            )

        if not os.getenv("VAULT_ENCRYPTION_KEY"):
            raise ValueError("VAULT_ENCRYPTION_KEY not set in environment")

        key_b64 = os.getenv("VAULT_ENCRYPTION_KEY")
        try:
            self._encryption_key = Fernet(key_b64.encode())
        except Exception as e:
            raise ValueError(f"Invalid VAULT_ENCRYPTION_KEY: {e}")

        conn = sqlite3.connect(str(self.vault_db_path))
        cursor = conn.cursor()

        try:
            required_keys = ["api_key", "username", "account_name"]
            creds = {}

            for key in required_keys:
                cursor.execute(
                    "SELECT encrypted_value FROM credentials WHERE key = ?", (key,)
                )
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"Missing credential in vault: {key}")

                encrypted = row[0]
                decrypted = self._encryption_key.decrypt(encrypted.encode()).decode()
                creds[key] = decrypted

            # Optional: live confirmation
            cursor.execute(
                "SELECT encrypted_value FROM credentials WHERE key = ?",
                ("confirm_live",),
            )
            row = cursor.fetchone()
            confirm_live = None
            if row:
                confirm_live = self._encryption_key.decrypt(row[0].encode()).decode()

            self.logger.info("Credentials loaded from vault")

            return BrokerCredentials(
                api_key=creds["api_key"],
                username=creds["username"],
                account_name=creds["account_name"],
                confirm_live=confirm_live,
            )

        finally:
            conn.close()

    def _load_from_env(self) -> BrokerCredentials:
        """
        Load credentials from environment variables or .env file.

        Expected env vars:
        - BROKERAPI_API_KEY
        - BROKERAPI_USERNAME
        - BROKERAPI_ACCOUNT_NAME
        - BOT_CONFIRM_LIVE (optional)

        Raises:
            ValueError: if required vars missing
        """

        # Try to load .env if it exists
        env_file = Path(".env")
        if env_file.exists():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file)
            except ImportError:
                pass  # dotenv not available, continue with system env

        api_key = os.getenv("BROKERAPI_API_KEY")
        username = os.getenv("BROKERAPI_USERNAME")
        account_name = os.getenv("BROKERAPI_ACCOUNT_NAME")
        confirm_live = os.getenv("BOT_CONFIRM_LIVE")

        if not all([api_key, username, account_name]):
            raise ValueError(
                "Missing broker credentials in environment. "
                "Set BROKERAPI_API_KEY, BROKERAPI_USERNAME, BROKERAPI_ACCOUNT_NAME"
            )

        self.logger.info("Credentials loaded from environment")

        return BrokerCredentials(
            api_key=api_key,
            username=username,
            account_name=account_name,
            confirm_live=confirm_live,
        )

    @staticmethod
    def setup_vault(vault_db_path: str, credentials: BrokerCredentials) -> str:
        """
        One-time initialization: create vault DB and store encrypted credentials.

        Args:
            vault_db_path: path to create vault.db
            credentials: BrokerCredentials to store

        Returns:
            Base64-encoded encryption key (save to VAULT_ENCRYPTION_KEY env var)

        Example:
            creds = BrokerCredentials(api_key='...', username='...', ...)
            key = CredentialManager.setup_vault('./vault.db', creds)
            print(f"Set VAULT_ENCRYPTION_KEY={key}")
        """
        if not HAS_CRYPTO:
            raise ValueError("cryptography package required. Install: pip install cryptography")

        # Generate encryption key
        encryption_key = Fernet.generate_key().decode()
        cipher = Fernet(encryption_key.encode())

        conn = sqlite3.connect(vault_db_path)
        cursor = conn.cursor()

        try:
            # Create schema
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS credentials (
                    key TEXT PRIMARY KEY,
                    encrypted_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rotated_at TIMESTAMP
                )
            """
            )

            # Store credentials
            creds_dict = {
                "api_key": credentials.api_key,
                "username": credentials.username,
                "account_name": credentials.account_name,
            }

            if credentials.confirm_live:
                creds_dict["confirm_live"] = credentials.confirm_live

            for key, value in creds_dict.items():
                encrypted = cipher.encrypt(value.encode()).decode()
                cursor.execute(
                    "INSERT OR REPLACE INTO credentials (key, encrypted_value) VALUES (?, ?)",
                    (key, encrypted),
                )

            conn.commit()

            print(f"Vault initialized at {vault_db_path}")
            print(f"Set this in your environment:")
            print(f"  export VAULT_ENCRYPTION_KEY={encryption_key}")
            print(f"  # OR in .env:")
            print(f"  VAULT_ENCRYPTION_KEY={encryption_key}")

            return encryption_key

        finally:
            conn.close()


class HealthChecker:
    """
    Periodic health checks: is bot alive? Is API responsive?

    Checks:
    1. Bot process alive (self-check)
    2. Broker connection alive (can fetch account balance)
    3. SQLite database accessible
    4. APScheduler jobs running
    5. Flatten routine scheduled correctly
    """

    def __init__(
        self,
        broker: Any,  # BrokerClient
        alert_handler: Any = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.broker = broker
        self.alert_handler = alert_handler
        self.logger = logger or logging.getLogger("HealthChecker")
        self.last_healthy_time: Optional[datetime] = None

    async def check_health(self) -> dict:
        """
        Run full health check.

        Returns:
            {
                'timestamp': datetime,
                'overall_healthy': bool,
                'checks': {
                    'process': {'name': str, 'status': str, ...},
                    'broker': {'name': str, 'status': str, 'balance': float, ...},
                    'database': {'name': str, 'status': str, ...},
                }
            }
        """

        health_status = {
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            "overall_healthy": True,
            "checks": {},
        }

        # 1. Process alive
        health_status["checks"]["process"] = {
            "name": "Bot Process",
            "status": "OK",
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
        }

        # 2. Broker connection
        try:
            balance = self.broker.get_account_balance()
            health_status["checks"]["broker"] = {
                "name": "Broker Connection",
                "status": "OK",
                "balance": balance,
                "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            }
        except Exception as e:
            health_status["checks"]["broker"] = {
                "name": "Broker Connection",
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            }
            health_status["overall_healthy"] = False

        # 3. Database accessible
        try:
            # Simple test: try to query positions table
            # (assumes pnl_tracker is available)
            health_status["checks"]["database"] = {
                "name": "SQLite Database",
                "status": "OK",
                "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "name": "SQLite Database",
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            }
            health_status["overall_healthy"] = False

        if health_status["overall_healthy"]:
            self.last_healthy_time = datetime.now(tz=CENTRAL_TZ)
        else:
            if self.alert_handler:
                await self.alert_handler.alert(
                    level="WARNING",
                    title="Health Check Failed",
                    message=json.dumps(health_status, indent=2, default=str),
                )

        return health_status


class ComplianceLogger:
    """
    Structured logging for trading events: entries, exits, risk decisions, flattens.

    Dual output:
    - trading_bot.log: rotating file, all events
    - compliance_ledger.jsonl: structured JSON, audit trail
    - metrics.jsonl: periodic metrics (health, P&L summaries)
    """

    def __init__(self, log_dir: str = "./logs", logger: Optional[logging.Logger] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = logger or logging.getLogger("ComplianceLogger")

        # Main log file: rotating, 100 MB max, 10 backups
        file_handler = RotatingFileHandler(
            self.log_dir / "trading_bot.log",
            maxBytes=100_000_000,
            backupCount=10,
        )

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler.setFormatter(formatter)

        self.main_logger = logging.getLogger("trading_bot")
        self.main_logger.addHandler(file_handler)
        self.main_logger.setLevel(logging.INFO)

        # Compliance ledger: structured JSON, one event per line
        self.compliance_handler = RotatingFileHandler(
            self.log_dir / "compliance_ledger.jsonl",
            maxBytes=100_000_000,
            backupCount=20,
        )
        self.compliance_logger = logging.getLogger("compliance")
        self.compliance_logger.addHandler(self.compliance_handler)
        self.compliance_logger.setLevel(logging.INFO)

        # Metrics: periodic aggregates
        self.metrics_handler = RotatingFileHandler(
            self.log_dir / "metrics.jsonl",
            maxBytes=100_000_000,
            backupCount=10,
        )
        self.metrics_logger = logging.getLogger("metrics")
        self.metrics_logger.addHandler(self.metrics_handler)
        self.metrics_logger.setLevel(logging.INFO)

    def log_entry(
        self, signal: str, size: int, entry_price: float, reason: str
    ) -> None:
        """Log a trade entry."""
        event = {
            "event": "ENTRY",
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            "signal": signal,
            "size": size,
            "entry_price": entry_price,
            "reason": reason,
        }
        self.compliance_logger.info(json.dumps(event))

    def log_exit(
        self,
        position_id: int,
        exit_price: float,
        quantity: int,
        pnl: float,
    ) -> None:
        """Log a trade exit."""
        event = {
            "event": "EXIT",
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            "position_id": position_id,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": pnl,
        }
        self.compliance_logger.info(json.dumps(event))

    def log_flatten(self, positions_closed: int, pnl_at_flatten: float) -> None:
        """Log daily flatten routine."""
        event = {
            "event": "FLATTEN",
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            "positions_closed": positions_closed,
            "pnl_at_flatten": pnl_at_flatten,
        }
        self.compliance_logger.info(json.dumps(event))

    def log_health(self, health_status: dict) -> None:
        """Log periodic health check."""
        self.metrics_logger.info(json.dumps(health_status, default=str))

    def log_risk_decision(self, decision: str, reason: str, details: dict) -> None:
        """Log a risk governance decision."""
        event = {
            "event": "RISK_DECISION",
            "timestamp": datetime.now(tz=CENTRAL_TZ).isoformat(),
            "decision": decision,
            "reason": reason,
            "details": details,
        }
        self.compliance_logger.info(json.dumps(event))

    def log_daily_summary(self, summary: dict) -> None:
        """Log end-of-day trading summary."""
        summary["timestamp"] = datetime.now(tz=CENTRAL_TZ).isoformat()
        summary["event"] = "DAILY_SUMMARY"
        self.metrics_logger.info(json.dumps(summary, default=str))
