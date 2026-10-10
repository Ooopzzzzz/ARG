import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.models import Agent


def issue_agent_key() -> str:
    return f"arg_{secrets.token_urlsafe(32)}"


def digest_agent_key(key: str) -> str:
    pepper = get_settings().agent_key_pepper.encode()
    return hmac.new(pepper, key.encode(), hashlib.sha256).hexdigest()


def require_operator(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Operator authentication required")
    token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(token, settings.operator_token):
        raise HTTPException(status_code=403, detail="Operator access denied")


def require_agent(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Agent:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Agent authentication required")
    digest = digest_agent_key(authorization.removeprefix("Bearer "))
    agent = session.scalar(select(Agent).where(Agent.key_digest == digest, Agent.enabled.is_(True)))
    if agent is None:
        raise HTTPException(status_code=401, detail="Invalid agent credential")
    return agent
