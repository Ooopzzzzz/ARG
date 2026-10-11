import logging
import os
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
LOGGER = logging.getLogger(__name__)


def main() -> None:
    database_password = secrets.token_urlsafe(24)
    values = {
        "POSTGRES_DB": "arg",
        "POSTGRES_USER": "arg",
        "POSTGRES_PASSWORD": database_password,
        "DATABASE_URL": f"postgresql+psycopg://arg:{database_password}@db:5432/arg",
        "AGENT_KEY_PEPPER": secrets.token_urlsafe(48),
        "OPERATOR_TOKEN": secrets.token_urlsafe(36),
        "ARG_DEMO_AGENT_KEY": f"arg_{secrets.token_urlsafe(36)}",
        "ARG_ERP_SHARED_SECRET": secrets.token_urlsafe(48),
        "CORS_ORIGINS": "http://localhost:3000",
        "API_URL": "http://api:8000",
    }
    descriptor = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as env_file:
        env_file.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    LOGGER.info("Created .env with local random secrets. Keep it out of Git.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
