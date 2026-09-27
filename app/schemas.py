"""Pydantic schemas matching the OpenAI Chat Completions API specification."""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single message in a chat completion conversation."""

    role: Literal["system", "user", "assistant"] = "user"
    content: str


class ChatCompletionRequest(BaseModel):
    """Payload sent by the Even companion app to /v1/chat/completions."""

    model: Optional[str] = "gemini-2.5-flash"
    messages: List[ChatMessage] = Field(default_factory=list)
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 150
    stream: Optional[bool] = False
    # Allow extra client fields without raising validation errors
    extra: Optional[Dict[str, Any]] = None


class ChatCompletionChoiceMessage(BaseModel):
    """Assistant message in a completion choice."""

    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    """Choice item in the chat completion response."""

    index: int = 0
    message: ChatCompletionChoiceMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionUsage(BaseModel):
    """Token usage metadata."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Standard OpenAI-compatible chat completion response."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "gemini-2.5-flash"
    choices: List[ChatCompletionChoice] = Field(default_factory=list)
    usage: Optional[ChatCompletionUsage] = Field(default_factory=ChatCompletionUsage)


# Streaming chunk schemas (SSE)
class ChatCompletionStreamChoiceDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatCompletionStreamChoice(BaseModel):
    index: int = 0
    delta: ChatCompletionStreamChoiceDelta
    finish_reason: Optional[str] = None


class ChatCompletionStreamChunk(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "gemini-2.5-flash"
    choices: List[ChatCompletionStreamChoice] = Field(default_factory=list)


# Models endpoint schemas
class ModelItem(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "google"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelItem] = Field(default_factory=list)
