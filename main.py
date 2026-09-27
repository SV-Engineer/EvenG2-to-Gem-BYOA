"""Root launcher for EvenG2-to-Gem-BYOA bridge server."""

import uvicorn
from app.config import settings


def main():
    """Starts the Uvicorn ASGI server."""
    print("=" * 65)
    print(" Starting EvenG2-to-Gem-BYOA Bridge")
    print(f" Listening on: http://{settings.HOST}:{settings.PORT}")
    print(f" Target Model: {settings.GEMINI_MODEL}")
    print(f" Mock Mode:    {settings.MOCK_GEMINI}")
    print(f" Auth Enforced:{bool(settings.PROXY_API_KEY)}")
    print("=" * 65)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
