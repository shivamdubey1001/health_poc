from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        schema: dict | None = None,
        schema_name: str = "result",
    ) -> tuple[dict, dict]:
        """Return (parsed_json, usage_metadata)."""
        raise NotImplementedError
