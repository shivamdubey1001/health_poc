import json
import httpx
from app.agents.base import LLMProvider
from app.config import settings


class OpenAIProvider(LLMProvider):
    """Minimal server-side client for the OpenAI Responses API.

    The API key is read only from backend environment settings. It is never
    returned to or required by the React application.
    """

    async def generate_json(self, *, system_prompt: str, user_payload: dict) -> tuple[dict, dict]:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Copy backend/.env.example to backend/.env and add your key."
            )

        prompt = (
            system_prompt
            + "\n\nReturn one valid JSON object only. Do not include markdown fences, hidden reasoning, "
              "or any text outside the JSON object.\n\nINPUT DATA:\n"
            + json.dumps(user_payload, default=str, ensure_ascii=False)
        )

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.openai_model,
                        "input": prompt,
                        "store": False,
                        "text": {"format": {"type": "json_object"}},
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000]
            raise RuntimeError(f"OpenAI API returned {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Could not reach OpenAI API: {exc}") from exc

        text = body.get("output_text")
        if not text:
            parts: list[str] = []
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        parts.append(content.get("text", ""))
            text = "\n".join(parts)
        if not text:
            raise RuntimeError("OpenAI response did not contain output text.")

        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            parsed = json.loads(cleaned.strip())
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI returned invalid JSON: {cleaned[:500]}") from exc

        usage = body.get("usage") or {}
        return parsed, {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "mode": "OPENAI",
            "model": settings.openai_model,
        }
