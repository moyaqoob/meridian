"""
Review generation: prompt + NVIDIA stream → ReviewOut JSON.

Prompt structure is load-bearing. Citations must use [CHUNK_ID: N].
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from core.config import settings
from models.schemas import ReviewOut
from models.tables import CodeChunk

SYSTEM_PROMPT = """
You are a senior software engineer performing a code review.
You have access to relevant context from the codebase retrieved specifically for this PR.

Your review must:
1. Focus on correctness, security, performance, and maintainability - in that order
2. Be specific: reference exact code, not vague observations
3. When referencing a code chunk, cite it as [CHUNK_ID: N] - never invent line numbers
4. Return a valid JSON object matching this schema - nothing else:
{
  "summary": string,
  "pr_type": "feat" | "fix" | "refactor" | "chore",
  "findings": [
    {
      "id": string,
      "severity": "high" | "medium" | "low",
      "category": string,
      "title": string,
      "comment": string,
      "file_path": string | null,
      "chunk_ref": string | null
    }
  ]
}

Severity definitions:
- high: will cause a bug, security issue, or data loss in production
- medium: likely to cause problems under load or edge cases
- low: style, readability, or minor improvement suggestions

Be direct. Be honest. If the PR is clean, say so briefly.
Do not pad the review with praise.
""".strip()


class ReviewParseError(Exception):
    """LLM returned malformed JSON."""


OnChunk = Callable[[str], Awaitable[None] | None]


def format_chunks_for_prompt(chunks: list[CodeChunk]) -> str:
    """
    Format retrieved chunks so the LLM can reference them by index id.
    Without explicit IDs, the LLM invents line numbers.
    """
    parts: list[str] = []
    for i, chunk in enumerate(chunks):
        parts.append(
            f"[CHUNK_ID: {i}] {chunk.file_path} lines {chunk.start_line}-{chunk.end_line}\n"
            f"```{chunk.language}\n{chunk.content}\n```"
        )
    return "\n\n".join(parts)


def _extract_json_object(response: str) -> dict[str, Any]:
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ReviewParseError("No JSON object found in model response")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ReviewParseError("Parsed JSON was not an object")
    return data


def parse_review_json(response: str, *, pr_id: str) -> ReviewOut:
    """Parse the LLM JSON into ReviewOut. Fills server-owned fields."""
    try:
        data = _extract_json_object(response)
        findings = data.get("findings") or []
        if isinstance(findings, list):
            for i, finding in enumerate(findings):
                if isinstance(finding, dict) and not finding.get("id"):
                    finding["id"] = f"finding-{i + 1}"

        return ReviewOut(
            review_id=str(uuid.uuid4()),
            pr_id=pr_id,
            summary=str(data.get("summary") or ""),
            pr_type=data.get("pr_type") or "chore",
            findings=findings,
            model_version=settings.llm_model,
            timings={},
        )
    except (json.JSONDecodeError, ValidationError, TypeError, ReviewParseError) as exc:
        raise ReviewParseError(f"Failed to parse review JSON: {exc}") from exc


def _nvidia_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.nvidia_api_key.get_secret_value(),
        base_url=settings.nvidia_api_base_url,
    )


async def generate_review(
    *,
    pr_id: str,
    diff: str,
    chunks: list[CodeChunk],
    on_chunk: OnChunk | None = None,
) -> ReviewOut:
    """
    Assemble the prompt, stream NVIDIA chat completions, parse ReviewOut.
    on_chunk is optional (SSE wiring lives in pipeline_events later).
    """
    context_block = format_chunks_for_prompt(chunks)
    user_message = f"""## PR Diff

{diff}

## Relevant Codebase Context

{context_block}

## Instructions

Review this PR. Return only a valid JSON object matching the schema in the system prompt.
Cite code references using [CHUNK_ID: N] syntax.
"""

    client = _nvidia_client()
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        max_tokens=4096,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    full_response = ""
    async for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta.content
        if not delta:
            continue
        full_response += delta
        if on_chunk is not None:
            result = on_chunk(delta)
            if isinstance(result, Awaitable):
                await result

    return parse_review_json(full_response, pr_id=pr_id)
