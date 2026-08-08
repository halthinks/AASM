from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .economics import CallPurpose, ModelUsageRecord


class OpenAIExecutorError(RuntimeError):
    pass


@dataclass
class OpenAIExecutionResult:
    output_text: str
    response_id: str | None
    model: str
    usage: ModelUsageRecord
    raw: dict[str, Any]


class OpenAIResponsesExecutor:
    """Small dependency-free Responses API adapter.

    This adapter deliberately does not invent hidden subagents. It sends a real
    Responses API request to the explicitly selected model. Higher-level AASM
    workers may create many such executors on different hosts in parallel.
    """

    def __init__(self, api_key: str | None = None, *, base_url: str = "https://api.openai.com/v1", timeout: float = 300.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        parts: list[str] = []
        for item in payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    def run(
        self,
        prompt: str,
        *,
        model: str,
        purpose: str = CallPurpose.PRODUCTIVE.value,
        instructions: str | None = None,
        reasoning_effort: str | None = None,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OpenAIExecutionResult:
        body: dict[str, Any] = {"model": model, "input": prompt}
        if instructions:
            body["instructions"] = instructions
        if reasoning_effort:
            body["reasoning"] = {"effort": reasoning_effort}
        req = Request(
            self.base_url + "/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise OpenAIExecutorError(f"OpenAI Responses API HTTP {exc.code}: {message}") from exc

        usage_raw = payload.get("usage", {}) or {}
        input_details = usage_raw.get("input_tokens_details", {}) or {}
        usage = ModelUsageRecord(
            model_id=payload.get("model", model),
            purpose=purpose,
            input_tokens=int(usage_raw.get("input_tokens", 0) or 0),
            cached_input_tokens=int(input_details.get("cached_tokens", 0) or 0),
            output_tokens=int(usage_raw.get("output_tokens", 0) or 0),
            task_id=task_id,
            metadata=dict(metadata or {}),
        )
        return OpenAIExecutionResult(
            output_text=self._extract_text(payload),
            response_id=payload.get("id"),
            model=payload.get("model", model),
            usage=usage,
            raw=payload,
        )
