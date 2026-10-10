import base64
import hashlib
import hmac
import json
import time
from typing import Any


def canonical_json(data: dict[str, Any]) -> str:
    """Produces deterministic compact JSON representation with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def create_proof_token(
    request_id: str,
    action_hash: str,
    action: dict[str, Any],
    secret: str,
    ttl_seconds: int = 300,
) -> str:
    """
    Mints a cryptographic HMAC-SHA256 proof token verifying that ARG authorized this specific action.
    Format: base64(header).base64(payload).signature
    """
    header = {"alg": "HS256", "typ": "ARG-EXECUTION-GRANT"}
    payload = {
        "rid": request_id,
        "ahash": action_hash,
        "action": action,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_seconds,
    }

    hdr_b64 = base64.urlsafe_b64encode(canonical_json(header).encode()).decode().rstrip("=")
    pay_b64 = base64.urlsafe_b64encode(canonical_json(payload).encode()).decode().rstrip("=")
    signing_input = f"{hdr_b64}.{pay_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).hexdigest()
    return f"{hdr_b64}.{pay_b64}.{signature}"


def verify_proof_token(token: str, secret: str) -> dict[str, Any]:
    """
    Verifies that the proof token has a valid HMAC signature and has not expired.
    Returns the payload dictionary on success, or raises ValueError.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid proof token format")

    hdr_b64, pay_b64, signature = parts
    signing_input = f"{hdr_b64}.{pay_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise ValueError("Cryptographic signature mismatch")

    # Decode payload
    padding = "=" * (-len(pay_b64) % 4)
    payload_raw = base64.urlsafe_b64decode(f"{pay_b64}{padding}")
    payload = json.loads(payload_raw.decode())

    now = int(time.time())
    if payload.get("exp", 0) < now:
        raise ValueError("Execution grant proof token has expired")

    return payload
