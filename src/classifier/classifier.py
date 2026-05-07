import json

import anthropic
from dotenv import load_dotenv

from .models import ClassificationResult

load_dotenv()

MODEL = "claude-sonnet-4-20250514"

_SYSTEM_PROMPT = """\
You are a content policy classifier. Given a policy document and a piece of content, \
classify whether the content is allowed, borderline, or violating according to the policy.

Verdict definitions:
- "allowed": Content clearly complies with the policy.
- "borderline": Content may or may not violate the policy; context or intent is ambiguous.
- "violating": Content clearly violates one or more policy rules.

When assessing content, apply the standard a professional Trust and Safety reviewer would use: \
if content could reasonably be interpreted as hostile, threatening, or harmful by a targeted \
person or group — even if it stops short of explicit policy language — classify it as borderline \
minimum, not allowed. Do not require explicit threats or slurs to reach a borderline verdict. \
Ambiguity should resolve toward caution, not permissiveness. Reserve "allowed" for content that \
a reasonable T&S reviewer would have no hesitation approving.

Always cite the specific section(s) from the policy that are most relevant to your verdict. \
Reasoning must be 1-2 sentences.\
"""

_TOOL = {
    "name": "classify_content",
    "description": "Record a structured content policy classification judgment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["allowed", "borderline", "violating"],
                "description": "The classification verdict.",
            },
            "confidence_score": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Confidence in the verdict, between 0.0 and 1.0.",
            },
            "cited_sections": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": (
                    "Quoted excerpts or section references from the policy document "
                    "that support the verdict."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 sentence explanation of why the content received this verdict.",
            },
        },
        "required": ["verdict", "confidence_score", "cited_sections", "reasoning"],
    },
}


class ClassificationError(Exception):
    pass


def classify(content: str, policy_document: str) -> ClassificationResult:
    """Classify content against a policy document.

    The policy_document is sent with a cache breakpoint so repeated calls with
    the same policy avoid re-processing it (prompt caching).
    """
    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    # Cache system prompt + tool definition as a stable prefix.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "classify_content"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"POLICY DOCUMENT:\n\n{policy_document}",
                            # Cache the policy doc — it's long and static per session.
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": f"CONTENT TO CLASSIFY:\n\n{content}",
                        },
                    ],
                }
            ],
        )
    except anthropic.RateLimitError as e:
        raise ClassificationError(f"Rate limit exceeded: {e}") from e
    except anthropic.APIConnectionError as e:
        raise ClassificationError(f"Connection error: {e}") from e
    except anthropic.APIStatusError as e:
        raise ClassificationError(f"API error {e.status_code}: {e.message}") from e

    tool_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_block is None:
        raise ClassificationError("Model did not return a classification tool call.")

    data = dict(tool_block.input)
    if isinstance(data.get("cited_sections"), str):
        data["cited_sections"] = json.loads(data["cited_sections"])
    return ClassificationResult.model_validate(data)
