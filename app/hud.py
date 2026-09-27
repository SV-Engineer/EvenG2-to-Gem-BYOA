"""HUD formatting utilities: strips markdown and enforces smart glasses brevity."""

import re
from app.config import settings


def sanitize_for_hud(text: str) -> str:
    """Sanitizes text output to ensure clean display on the G2 MicroLED screen.

    Removes markdown formatting characters (asterisks, hashes, backticks, bullets)
    and enforces line breaks and character limits.
    """
    if not text:
        return ""

    cleaned = text

    # Strip bold and italic markdown (**text**, *text*, __text__, _text_)
    cleaned = re.sub(r"[*_]{1,3}(.*?)[*_]{1,3}", r"\1", cleaned)

    # Strip markdown headers (e.g. "# Title", "### Subtitle")
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)

    # Strip bullet points and list markers (-, *, +, 1.)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # Strip inline code backticks (`code`)
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)

    # Strip code block fences (```python ... ```)
    cleaned = re.sub(r"```[a-zA-Z]*\n?([\s\S]*?)```", r"\1", cleaned)

    # Collapse multiple spaces or newlines into clean single line/spaces
    cleaned = re.sub(r"\n+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    # Enforce maximum character cutoff if configured
    if settings.HUD_MAX_CHARACTERS > 0 and len(cleaned) > settings.HUD_MAX_CHARACTERS:
        cleaned = cleaned[: settings.HUD_MAX_CHARACTERS].rsplit(" ", 1)[0] + "..."

    return cleaned


def get_hud_system_prompt() -> str:
    """Returns the system prompt configured to instruct models for smart glasses."""
    return settings.HUD_SYSTEM_PROMPT
