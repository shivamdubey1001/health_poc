import json
import httpx
from app.agents.base import LLMProvider
from app.config import settings


class OpenAIProvider(LLMProvider):
    async def generate_json(self, *, system_prompt: str, user_payload: dict) -> tuple[dict, dict]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_AI=false")
        prompt = (
            system_prompt
            + "\n\nReturn only valid JSON. Do not include markdown fences or hidden reasoning.\n\nINPUT:\n"
            + json.dumps(user_payload, default=str)
        )
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
                json={"model": settings.openai_model, "input": prompt, "store": False},
            )
            response.raise_for_status()
            body = response.json()
        text = body.get("output_text")
        if not text:
            parts = []
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        parts.append(content.get("text", ""))
            text = "\n".join(parts)
        parsed = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
        usage = body.get("usage") or {}
        return parsed, {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "mode": "OPENAI",
        }
