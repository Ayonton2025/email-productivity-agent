"""Provider adapter protocol."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class EmailProviderAdapter(ABC):
    @abstractmethod
    async def send(self, transport: Any, payload: Dict[str, Any]) -> bool:
        """Send one normalized email payload."""
