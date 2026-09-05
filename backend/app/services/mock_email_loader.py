"""Load deterministic mock email data for local and test mode."""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.exceptions import EmailDataLoadError


class MockEmailLoader:
    """Resolve mock inbox data from disk with a deterministic local fallback."""

    paths = (
        "data/mock_inbox.json",
        "./data/mock_inbox.json",
        "backend/data/mock_inbox.json",
        "./backend/data/mock_inbox.json",
        "../data/mock_inbox.json",
        "./../data/mock_inbox.json",
    )

    def load(self, fallback=None) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for file_path in self.paths:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as file_handle:
                    return json.load(file_handle)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                last_error = exc

        if last_error is not None:
            raise EmailDataLoadError(
                "Unable to load mock email data",
                details={"cause": type(last_error).__name__},
            ) from last_error

        return fallback() if fallback else self._fallback()

    @staticmethod
    def _fallback() -> list[dict[str, Any]]:
        return [
            {
                "id": str(index),
                "sender": f"sender{index}@example.test",
                "subject": f"Mock email {index}",
                "body": f"This is deterministic mock email number {index}.",
                "timestamp": "2024-01-08T10:30:00Z",
                "category": "Updates",
                "priority": "medium",
                "is_read": index % 2 == 0,
                "is_archived": False,
                "is_starred": False,
                "action_items": [],
                "summary": f"Summary for mock email {index}.",
            }
            for index in range(1, 21)
        ]
