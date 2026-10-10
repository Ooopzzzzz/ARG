from typing import Any


def execute_mock_action(action: dict[str, Any]) -> dict[str, str]:
    return {
        "adapter": "mock",
        "message": "Simulated action completed",
        "target": str(action["target"]),
    }
