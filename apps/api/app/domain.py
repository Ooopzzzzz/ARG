import hashlib
import json
from typing import Any


def canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def risk_assessment(action: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    amount = action.get("impact", {}).get("amount", 0)
    factors: list[dict[str, Any]] = [
        {
            "name": "environment",
            "points": 20 if action.get("environment") == "production" else 0,
            "reason": "Production environment"
            if action.get("environment") == "production"
            else "Non-production environment",
        },
        {
            "name": "classification",
            "points": 20 if action.get("data_classification") == "restricted" else 5,
            "reason": f"Data classification: {action.get('data_classification', 'unknown')}",
        },
        {
            "name": "impact",
            "points": min(40, int(max(0, amount) / 100)),
            "reason": "Impact magnitude is assessed from the declared amount",
        },
    ]
    return min(100, sum(int(factor["points"]) for factor in factors)), factors


def evaluate_policy(
    action: dict[str, Any], rules: list[dict[str, Any]], risk: int
) -> tuple[str, list[str]]:
    matches: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("action_type") not in ("*", action.get("type")):
            continue
        target = rule.get("target")
        if target is not None and target != action.get("target"):
            continue
        threshold = rule.get("min_risk")
        if threshold is not None and risk < int(threshold):
            continue
        matches.append(rule)
    if any(rule.get("effect") == "DENY" for rule in matches):
        return "DENY", [
            str(rule.get("reason_code", "POLICY_DENY"))
            for rule in matches
            if rule.get("effect") == "DENY"
        ]
    if any(rule.get("effect") == "REQUIRE_APPROVAL" for rule in matches):
        return "REQUIRE_APPROVAL", [
            str(rule.get("reason_code", "POLICY_APPROVAL_REQUIRED"))
            for rule in matches
            if rule.get("effect") == "REQUIRE_APPROVAL"
        ]
    if any(rule.get("effect") == "ALLOW" for rule in matches):
        return "ALLOW", [
            str(rule.get("reason_code", "POLICY_ALLOWED"))
            for rule in matches
            if rule.get("effect") == "ALLOW"
        ]
    return "DENY", ["DEFAULT_DENY"]
