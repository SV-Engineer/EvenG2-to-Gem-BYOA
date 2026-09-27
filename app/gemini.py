"""Client wrapper for Google Gemini models using the official google-genai SDK."""

import asyncio
import logging
from typing import AsyncGenerator, List
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.config import settings
from app.hud import get_hud_system_prompt, sanitize_for_hud
from app.schemas import ChatMessage

logger = logging.getLogger("eveng2.gemini")


class GeminiBridge:
    """Bridges OpenAI-style chat messages to Google Gemini with automatic fallback and retries."""

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

    def _get_candidate_models(self) -> List[str]:
        """Returns ordered list of models to try if the primary encounters 503 high demand."""
        candidates = [
            settings.GEMINI_MODEL,
            "gemini-flash-latest",
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
        ]
        # Deduplicate while preserving order
        return list(dict.fromkeys(c for c in candidates if c))

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

        candidate_models = self._get_candidate_models()
        last_error = None

        for model_name in candidate_models:
            for attempt in range(2):  # Try each model up to twice (immediate retry on spike)
                try:
                    logger.info(
                        f"Dispatching query to Gemini model: {model_name} (attempt {attempt + 1})"
                    )
                    response = await self.client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    raw_text = response.text or ""
                    return sanitize_for_hud(raw_text)

                except (ServerError, ClientError) as err:
                    last_error = err
                    err_msg = str(err)
                    logger.warning(
                        f"Model {model_name} encountered error: {err_msg[:120]}..."
                    )

                    # Only retry on 503 high demand or 429 rate limit
                    if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg:
                        if attempt == 0:
                            await asyncio.sleep(0.3)
                            continue
                        # If attempt 1 fails, fall through to try next candidate model
                        break
                    else:
                        # Non-recoverable error (e.g. invalid request format)
                        raise

        logger.error(f"All candidate models exhausted. Last error: {last_error}")
        return "Gemini is currently experiencing high demand. Please try again in a few moments."

    async def generate_stream(
        self, messages: List[ChatMessage], temperature: float | None = 0.7
    ) -> AsyncGenerator[str, None]:
        """Yields streaming chunks of text for lowest latency with fallback support."""
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

        candidate_models = self._get_candidate_models()
        streamed_any = False

        for model_name in candidate_models:
            try:
                logger.info(f"Streaming query from Gemini model: {model_name}")
                async for chunk in await self.client.aio.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        streamed_any = True
                        yield chunk.text

                # If successful, exit
                if streamed_any:
                    return

            except (ServerError, ClientError) as err:
                err_msg = str(err)
                logger.warning(
                    f"Streaming error on model {model_name}: {err_msg[:120]}..."
                )
                if not streamed_any and ("503" in err_msg or "429" in err_msg):
                    # Try next candidate model if nothing was sent yet
                    continue
                else:
                    break

        if not streamed_any:
            yield "Gemini is currently busy. Please try again shortly."


gemini_bridge = GeminiBridge()
