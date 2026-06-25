"""
PulseOps — Core AI Service
Uses OpenRouter (OpenAI-compatible) for all chat completions.
Structured outputs via JSON mode + Pydantic parsing.
"""
import json
import ssl
import httpx
from typing import Any, Type
from openai import AsyncOpenAI
from pydantic import BaseModel
from app.core.config import settings

# Corporate proxies often intercept TLS — disable verification so OpenRouter calls succeed
_http_client = httpx.AsyncClient(verify=False)

# OpenRouter client — drop-in replacement for OpenAI SDK
client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
    http_client=_http_client,
    default_headers={
        "HTTP-Referer": "https://pulseops.ai",   # OpenRouter requires this
        "X-Title": "PulseOps",
    },
)

MODEL = settings.OPENROUTER_MODEL  # "openai/gpt-4o"


def _schema_hint(model: Type[BaseModel]) -> str:
    """Render a compact JSON schema hint to inject into system prompts."""
    schema = model.model_json_schema()
    props = schema.get("properties", {})
    lines = []
    for field, meta in props.items():
        t = meta.get("type", meta.get("anyOf", "any"))
        lines.append(f'  "{field}": {t}')
    return "{\n" + ",\n".join(lines) + "\n}"


async def structured_completion(
    system_prompt: str,
    user_prompt: str,
    response_model: Type[BaseModel],
    temperature: float = 0.3,
) -> BaseModel:
    """
    Call GPT-4o via OpenRouter with JSON mode.
    Parses the response into the given Pydantic model.
    """
    # Inject schema into system prompt so the model knows the expected shape
    schema_str = _schema_hint(response_model)
    full_system = (
        f"{system_prompt}\n\n"
        f"You MUST respond with ONLY valid JSON matching this exact structure:\n"
        f"{schema_str}\n"
        f"No markdown, no code blocks, no explanation — raw JSON only."
    )

    response = await client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown code fences if the model adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)
    return response_model.model_validate(data)


async def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.5,
    history: list[dict] | None = None,
) -> str:
    """Plain text completion — for summaries, reports, free-form answers."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})
    response = await client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


# ── Prompt Templates ──────────────────────────────────────────────────────────

INTAKE_SYSTEM = """You are PulseOps AI, an expert operational intelligence assistant.
Your job is to analyze a raw project/task request and extract structured information.

Rules:
- Generate a clear, professional title (max 10 words)
- Write a concise description (2-4 sentences) explaining what needs to be done and why
- Suggest realistic tags (3-6 tags, lowercase, hyphenated)
- Suggest 3-5 concrete subtasks as plain strings
- Suggest 2-4 immediate next steps as plain strings
- Suggest a realistic due date in ISO format YYYY-MM-DD (if unclear, use 30 days from today)
- Suggest a priority level: must be exactly one of: low, medium, high, urgent
- Suggest potential owners based on role names mentioned (or ["TBD"] if none mentioned)
- Write clear reasoning for your priority recommendation
- Never finalize priority — it is always a suggestion for human review
"""

EMAIL_SYSTEM = """You are PulseOps AI, an email intelligence assistant.
Analyze the email and extract all actionable work items.

Extract:
- A concise summary of the email (2-3 sentences)
- All tasks mentioned or implied (with assignee, deadline if mentioned)
- People mentioned with their roles/context
- Any deadlines mentioned (as list of objects with "date" and "context" keys)
- Any blockers mentioned

Be precise. Only extract tasks that are clearly implied or stated.
For extracted_tasks, each item must have: title, assignee (string or null), due_date (string or null), priority (low/medium/high/urgent), context (string or null).
"""

TRANSCRIPT_SYSTEM = """You are PulseOps AI, a meeting intelligence assistant.
Analyze the meeting transcript and extract structured operational information.

Extract:
- A concise meeting summary (3-5 sentences, covering purpose + outcomes)
- All action items with owner and deadline
- Key decisions made (list of strings)
- Blockers or risks mentioned (list of strings)
- List of attendees (names only, list of strings)

For action_items, each must have: task (string), owner (string or null), deadline (string or null), priority (low/medium/high/urgent).
"""

PRIORITY_SYSTEM = """You are PulseOps AI, a project prioritization expert.
Analyze the project and recommend an appropriate priority level.

Consider: due date urgency, business impact, blockers, stakeholder importance, inactivity, dependencies.

Return:
- suggested_priority: exactly one of: low, medium, high, urgent
- reasoning: 2-3 sentences explaining the recommendation
- factors: list of 3-5 key factors that drove the recommendation (list of strings)

This is a SUGGESTION. The human makes the final decision.
"""

HEALTH_SYSTEM = """You are PulseOps AI, a project health analyst.
Evaluate the project state and generate a health assessment.

Return:
- health_status: exactly one of: healthy, at_risk, delayed, blocked
- health_score: integer 0-100 (100 = perfectly on track)
- risk_score: integer 0-100 (0 = no risk, 100 = critical)
- delivery_confidence: integer 0-100 (confidence of on-time delivery)
- reasoning: 2-3 sentence explanation

Base assessment on: progress %, due date, blockers, last update, status.
"""

SUMMARY_SYSTEM = """You are PulseOps AI, an operational summary generator.
Generate a clear, concise operational summary in the requested format.

For daily: focus on what happened today and what's coming tomorrow.
For weekly: focus on week's progress, blockers encountered, and next week's priorities.
For executive: high-level status, key wins, critical risks, and resource needs.
For blocker: focus exclusively on blockers, their impact, and recommended unblocking actions.

Be professional, direct, and actionable. Use bullet points where appropriate.
"""
