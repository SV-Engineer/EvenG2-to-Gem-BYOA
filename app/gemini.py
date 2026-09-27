"""Client wrapper for Google Gemini models using the official google-genai SDK."""

import logging
from typing import AsyncGenerator, List
from google import genai
from google.genai import types

from app.config import settings
from app.hud import get_hud_system_prompt, sanitize_for_hud
from app.schemas import ChatMessage

logger = logging.getLogger("eveng2.gemini")


class GeminiBridge:
    """Bridges OpenAI-style chat messages to Google Gemini."""

    def __init__(self):
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Lazily instantiates the Gemini client."""
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please provide it in your .env file "
                    "or environment variables (obtainable at https://aistudio.google.com/)."
                )
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def convert_messages_to_contents(
        self, messages: List[ChatMessage]
    ) -> List[types.Content]:
        """Converts OpenAI message list to Gemini Content objects."""
        contents: List[types.Content] = []
        for msg in messages:
            if msg.role == "system":
                # System instructions are set in GenerateContentConfig
                continue
            role = "model" if msg.role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content)],
                )
            )
        return contents

    async def generate_response(
        self, messages: List[ChatMessage], temperature: float | None = 0.7
    ) -> str:
        """Sends chat history to Gemini and returns a sanitized HUD response string."""
        if settings.MOCK_GEMINI:
            logger.info("MOCK_GEMINI is enabled; returning simulated response.")
            return "This is a simulated G2 response. The bridge is running normally."

        contents = self.convert_messages_to_contents(messages)
        if not contents:
            return "No input text provided."

        config = types.GenerateContentConfig(
            system_instruction=get_hud_system_prompt(),
            max_output_tokens=150,
            temperature=temperature or 0.7,
        )

        model_name = settings.GEMINI_MODEL
        logger.info(f"Dispatching query to Gemini model: {model_name}")

        response = await self.client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        raw_text = response.text or ""
        return sanitize_for_hud(raw_text)

    async def generate_stream(
        self, messages: List[ChatMessage], temperature: float | None = 0.7
    ) -> AsyncGenerator[str, None]:
        """Yields streaming chunks of text for lowest latency."""
        if settings.MOCK_GEMINI:
            logger.info("MOCK_GEMINI is enabled; streaming simulated chunks.")
            mock_words = ["Simulated ", "response ", "from ", "the ", "bridge."]
            for word in mock_words:
                yield word
            return

        contents = self.convert_messages_to_contents(messages)
        if not contents:
            yield "No input text provided."
            return

        config = types.GenerateContentConfig(
            system_instruction=get_hud_system_prompt(),
            max_output_tokens=150,
            temperature=temperature or 0.7,
        )

        model_name = settings.GEMINI_MODEL
        async for chunk in await self.client.aio.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text


gemini_bridge = GeminiBridge()
