"""Simulates an Even Realities G2 companion app request to /v1/chat/completions.

Usage:
    python scripts/test_client.py
    python scripts/test_client.py --query "What is quantum computing?"
    python scripts/test_client.py --stream
    python scripts/test_client.py --test-auth
"""

import argparse
import os
import sys
import httpx
from dotenv import load_dotenv

# Load local .env so testing is automatic without retyping keys
load_dotenv()


def test_chat(
    url: str,
    key: str,
    query: str,
    stream: bool = False,
    test_auth: bool = False,
):
    endpoint = f"{url.rstrip('/')}/v1/chat/completions"
    health_endpoint = f"{url.rstrip('/')}/health"

    print(f"\n[1] Checking server health at {health_endpoint}...")
    try:
        health_resp = httpx.get(health_endpoint, timeout=5.0)
        print(f"    Health Status: {health_resp.status_code}")
        print(f"    Health Data:   {health_resp.json()}")
    except Exception as e:
        print(f"    [!] Failed to connect to server: {e}")
        print("    Ensure the bridge server is running: python main.py")
        sys.exit(1)

    headers = {"Content-Type": "application/json"}
    if test_auth:
        print("\n[2] Testing invalid auth token (expecting 401 Unauthorized)...")
        headers["Authorization"] = "Bearer WRONG_TOKEN_123"
    elif key:
        headers["Authorization"] = f"Bearer {key}"

    payload = {
        "model": "gemini-3.8-flash",
        "messages": [
            {"role": "user", "content": query},
        ],
        "temperature": 0.7,
        "stream": stream,
    }

    print(f"\n[3] Sending request to {endpoint}")
    print(f"    Query: '{query}'")
    print(f"    Stream: {stream}")

    try:
        if stream:
            with httpx.stream(
                "POST", endpoint, headers=headers, json=payload, timeout=30.0
            ) as response:
                print(f"    Response Status: {response.status_code}")
                if response.status_code != 200:
                    print(f"    Error: {response.read().decode('utf-8')}")
                    return
                print("\n[G2 Glasses HUD Display (Streamed)]:")
                print("-" * 50)
                for line in response.iter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            import json

                            chunk_json = json.loads(line[6:])
                            delta_content = (
                                chunk_json.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            print(delta_content, end="", flush=True)
                        except Exception:
                            pass
                print("\n" + "-" * 50)
        else:
            response = httpx.post(
                endpoint, headers=headers, json=payload, timeout=30.0
            )
            print(f"    Response Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200:
                reply = data["choices"][0]["message"]["content"]
                print("\n[G2 Glasses HUD Display]:")
                print("-" * 50)
                print(reply)
                print("-" * 50)
            else:
                print(f"    Error Response: {data}")

    except Exception as e:
        print(f"    [!] Error during request: {e}")


def main():
    parser = argparse.ArgumentParser(description="Even Realities G2 Mock Client")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the bridge (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--key",
        default=os.getenv("PROXY_API_KEY", ""),
        help="Bearer token (PROXY_API_KEY). Defaults to PROXY_API_KEY in .env.",
    )
    parser.add_argument(
        "--query",
        default="Briefly explain what photosynthesis is.",
        help="Question to ask Even AI",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Test streaming response mode",
    )
    parser.add_argument(
        "--test-auth",
        action="store_true",
        help="Send intentionally incorrect token to verify 401 rejection",
    )

    args = parser.parse_args()
    test_chat(
        url=args.url,
        key=args.key,
        query=args.query,
        stream=args.stream,
        test_auth=args.test_auth,
    )


if __name__ == "__main__":
    main()
