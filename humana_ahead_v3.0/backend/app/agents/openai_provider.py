import asyncio
import json
import random
import re
import uuid

import httpx

from app.agents.base import LLMProvider
from app.config import settings

# Transient conditions worth retrying. 429 is rate limiting; 5xx is provider-side.
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

# Counters surfaced on the Impact page. A fallback counter reading zero is far
# more convincing than having no counter at all.
COUNTERS = {"parse_repairs": 0, "transport_retries": 0, "schema_rejections": 0}


def reset_counters() -> None:
    for key in COUNTERS:
        COUNTERS[key] = 0


class OpenAIProvider(LLMProvider):
    """Server-side client for the OpenAI Responses API.

    The API key is read only from backend environment settings and is never
    returned to, or required by, the React application.

    Three reliability behaviours matter here:

    1. Determinism - temperature is pinned so the same payload yields the same
       assessment. Without this an evaluation number cannot be reproduced.
    2. Schema enforcement - when a JSON schema is supplied the API is asked to
       guarantee the shape rather than hoping the model complies.
    3. Repair - a single retry that hands the malformed text back with the
       schema, before failing the member. One bad character should not lose a
       whole assessment.
    """

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: dict,
        schema: dict | None = None,
        schema_name: str = "result",
    ) -> tuple[dict, dict]:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Copy backend/.env.example to "
                "backend/.env and add your key."
            )

        correlation_id = uuid.uuid4().hex[:12]
        prompt = (
            system_prompt
            + "\n\nReturn one valid JSON object only. Do not include markdown fences, "
              "hidden reasoning, or any text outside the JSON object.\n\nINPUT DATA:\n"
            + json.dumps(user_payload, default=str, ensure_ascii=False)
        )

        text, usage = await self._call(prompt, schema, schema_name)

        try:
            parsed = self._parse(text)
        except json.JSONDecodeError:
            # One repair attempt. Hand the malformed output back and ask for a fix.
            COUNTERS["parse_repairs"] += 1
            repair_prompt = (
                system_prompt
                + "\n\nYour previous response was not valid JSON. Return the same "
                  "information as ONE valid JSON object, with no fences and no "
                  "commentary.\n\nPREVIOUS INVALID RESPONSE:\n"
                + text[:4000]
                + "\n\nINPUT DATA:\n"
                + json.dumps(user_payload, default=str, ensure_ascii=False)
            )
            text2, usage2 = await self._call(repair_prompt, schema, schema_name)
            usage = {
                "input_tokens": (usage.get("input_tokens") or 0) + (usage2.get("input_tokens") or 0),
                "output_tokens": (usage.get("output_tokens") or 0) + (usage2.get("output_tokens") or 0),
            }
            try:
                parsed = self._parse(text2)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Model returned invalid JSON twice (correlation {correlation_id}): {text2[:400]}"
                ) from exc

        return parsed, {
            "input_tokens": usage.get("input_tokens") or 0,
            "output_tokens": usage.get("output_tokens") or 0,
            "mode": "OPENAI",
            "model": settings.openai_model,
            "correlation_id": correlation_id,
            "prompt_version": settings.prompt_version,
        }

    # ------------------------------------------------------------------ internals
    async def _call(self, prompt: str, schema, schema_name) -> tuple[str, dict]:
        if schema:
            text_format = {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            }
        else:
            text_format = {"format": {"type": "json_object"}}

        body = {
            "model": settings.openai_model,
            "input": prompt,
            "store": False,
            "temperature": settings.openai_temperature,
            "text": text_format,
        }

        last_error: Exception | None = None
        for attempt in range(settings.openai_max_retries):
            try:
                async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers={
                            "Authorization": f"Bearer {settings.openai_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )

                if response.status_code == 400:
                    # Some models reject strict schema or a temperature override.
                    # Degrade once rather than failing the member, and record it.
                    detail = response.text[:500].lower()
                    if ("schema" in detail or "temperature" in detail) and (
                        schema is not None or "temperature" in body
                    ):
                        COUNTERS["schema_rejections"] += 1
                        body["text"] = {"format": {"type": "json_object"}}
                        body.pop("temperature", None)
                        schema = None
                        continue

                if response.status_code in RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(
                        f"retryable {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                payload = response.json()
                return self._extract_text(payload), (payload.get("usage") or {})

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                if status not in RETRYABLE_STATUS or attempt == settings.openai_max_retries - 1:
                    detail = exc.response.text[:600] if exc.response is not None else str(exc)
                    raise RuntimeError(f"OpenAI API returned {status}: {detail}") from exc
                await self._backoff(attempt)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == settings.openai_max_retries - 1:
                    raise RuntimeError(f"Could not reach OpenAI API: {exc}") from exc
                await self._backoff(attempt)

        raise RuntimeError(f"OpenAI call failed after retries: {last_error}")

    @staticmethod
    async def _backoff(attempt: int) -> None:
        COUNTERS["transport_retries"] += 1
        delay = min(8.0, float(2 ** attempt)) + random.uniform(0, 0.4)
        await asyncio.sleep(delay)

    @staticmethod
    def _extract_text(body: dict) -> str:
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
        return text

    @staticmethod
    def _parse(text: str) -> dict:
        cleaned = re.sub(r"```(?:json)?|```", "", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.S)
            if not match:
                raise
            return json.loads(match.group(0))
