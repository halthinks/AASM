from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .economics import CallPurpose, ModelUsageRecord


class CodexExecutorError(RuntimeError):
    pass


@dataclass
class CodexExecutionResult:
    output_text: str
    thread_id: str | None
    model: str | None
    usage: ModelUsageRecord
    events: list[dict[str, Any]]


class CodexCLIExecutor:
    """Headless adapter around `codex exec --json`.

    AASM never enables unsafe permission modes implicitly. Sandbox/approval
    posture remains a Codex configuration concern. This adapter only selects a
    model, supplies the task, captures structured events, and returns usage.
    """

    def __init__(self, *, binary: str = "codex", cwd: str | Path | None = None, timeout: float = 1800.0, extra_args: list[str] | None = None):
        self.binary = binary
        self.cwd = None if cwd is None else str(cwd)
        self.timeout = timeout
        self.extra_args = list(extra_args or [])

    def run(
        self,
        prompt: str,
        *,
        model: str | None = None,
        purpose: str = CallPurpose.PRODUCTIVE.value,
        task_id: str | None = None,
    ) -> CodexExecutionResult:
        cmd = [self.binary, "exec", "--json"]
        if model:
            cmd += ["-m", model]
        cmd += self.extra_args
        cmd.append(prompt)
        try:
            proc = subprocess.run(cmd, cwd=self.cwd, text=True, capture_output=True, timeout=self.timeout, check=False)
        except FileNotFoundError as exc:
            raise CodexExecutorError(f"Codex CLI not found: {self.binary}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexExecutorError(f"Codex task exceeded {self.timeout}s") from exc
        if proc.returncode != 0:
            raise CodexExecutorError(proc.stderr.strip() or f"codex exited {proc.returncode}")

        events: list[dict[str, Any]] = []
        thread_id = None
        final_text = ""
        effective_model = model
        input_tokens = cached_tokens = output_tokens = 0
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(event)
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id") or event.get("thread", {}).get("id")
                effective_model = event.get("model") or effective_model
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                final_text = item.get("text", final_text)
            usage = event.get("usage") or event.get("token_usage") or {}
            input_tokens = max(input_tokens, int(usage.get("input_tokens", usage.get("input", 0)) or 0))
            cached_tokens = max(cached_tokens, int(usage.get("cached_input_tokens", usage.get("cached_input", 0)) or 0))
            output_tokens = max(output_tokens, int(usage.get("output_tokens", usage.get("output", 0)) or 0))

        usage_record = ModelUsageRecord(
            model_id=effective_model or "codex-unspecified",
            purpose=purpose,
            input_tokens=input_tokens,
            cached_input_tokens=cached_tokens,
            output_tokens=output_tokens,
            task_id=task_id,
            metadata={"executor": "codex_cli", "thread_id": thread_id},
        )
        return CodexExecutionResult(final_text, thread_id, effective_model, usage_record, events)
