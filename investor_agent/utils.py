"""Utility functions for the investor agent."""

import re


def strip_markdown_json(text: str) -> str:
    """
    Remove markdown code fences from JSON strings.

    LLMs sometimes wrap JSON in ```json ... ``` despite instructions.
    This utility strips those wrappers before Pydantic validation.

    Args:
        text: Raw LLM output that may contain markdown wrappers

    Returns:
        Clean JSON string without markdown code fences

    Examples:
        >>> strip_markdown_json('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'

        >>> strip_markdown_json('{"key": "value"}')  # Already clean
        '{"key": "value"}'
    """
    if not text:
        return text

    # Pattern matches: ```json ... ``` or ``` ... ```
    # Handles optional language identifier and whitespace
    pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(pattern, text.strip(), re.DOTALL)

    if match:
        return match.group(1).strip()

    return text.strip()
