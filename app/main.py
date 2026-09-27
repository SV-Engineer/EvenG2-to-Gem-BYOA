"""FastAPI application for the EvenG2-to-Gem-BYOA bridge server."""

import json
import logging
import time
from typing import AsyncGenerator
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app import __version__
from app.auth import verify_proxy_key
from app.config import settings
from app.gemini import gemini_bridge
from app.schemas import (
    ChatCompletionChoice,
    ChatCompletionChoiceMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamChoice,
    ChatCompletionStreamChoiceDelta,
    ChatCompletionStreamChunk,
    ModelItem,
    ModelListResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("eveng2.api")

app = FastAPI(
    title="EvenG2-to-Gem-BYOA",
    description="Bridge connecting Even Realities G2 smart glasses to Google Gemini models.",
    version=__version__,
)

# Enable CORS for cross-origin mobile and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Logs incoming request method, path, and duration."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)"
    )
    return response


@app.get("/")
async def root():
    """Root info endpoint."""
    return {
        "service": "EvenG2-to-Gem-BYOA",
        "version": __version__,
        "status": "online",
        "model": settings.GEMINI_MODEL,
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Diagnostic health check verifying configuration and readiness."""
    has_gemini_key = bool(settings.GEMINI_API_KEY)
    has_proxy_key = bool(settings.PROXY_API_KEY)

    return {
        "status": "healthy" if (has_gemini_key or settings.MOCK_GEMINI) else "degraded",
        "gemini_api_key_configured": has_gemini_key,
        "proxy_auth_enforced": has_proxy_key,
        "mock_mode": settings.MOCK_GEMINI,
        "model": settings.GEMINI_MODEL,
    }


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models(token: str = Depends(verify_proxy_key)):
    """OpenAI-compatible models listing."""
    return ModelListResponse(
        data=[
            ModelItem(id=settings.GEMINI_MODEL),
            ModelItem(id="gemini-3.8-flash"),
            ModelItem(id="gemini-flash-latest"),
        ]
    )


async def sse_stream_generator(
    request_data: ChatCompletionRequest,
) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) in OpenAI streaming format."""
    chunk_id = f"chatcmpl-{int(time.time())}"
    async for text_chunk in gemini_bridge.generate_stream(
        request_data.messages, temperature=request_data.temperature
    ):
        chunk = ChatCompletionStreamChunk(
            id=chunk_id,
            model=settings.GEMINI_MODEL,
            choices=[
                ChatCompletionStreamChoice(
                    delta=ChatCompletionStreamChoiceDelta(content=text_chunk),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"

    # Send final terminating chunk
    done_chunk = ChatCompletionStreamChunk(
        id=chunk_id,
        model=settings.GEMINI_MODEL,
        choices=[
            ChatCompletionStreamChoice(
                delta=ChatCompletionStreamChoiceDelta(),
                finish_reason="stop",
            )
        ],
    )
    yield f"data: {done_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    token: str = Depends(verify_proxy_key),
):
    """OpenAI-compatible chat completions endpoint called by Even Realities G2 companion app."""
    logger.debug(f"Received completion request with {len(body.messages)} message(s)")

    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request messages array cannot be empty.",
        )

    # Handle streaming if requested by client
    if body.stream:
        return StreamingResponse(
            sse_stream_generator(body),
            media_type="text/event-stream",
        )

    # Standard non-streaming response
    try:
        reply_text = await gemini_bridge.generate_response(
            body.messages, temperature=body.temperature
        )
        return ChatCompletionResponse(
            model=settings.GEMINI_MODEL,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionChoiceMessage(
                        role="assistant",
                        content=reply_text,
                    ),
                    finish_reason="stop",
                )
            ],
        )
    except Exception as e:
        logger.error(f"Error generating Gemini response: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backend Gemini error: {str(e)}",
        )
