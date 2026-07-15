#!/usr/bin/env python3
"""Quick test for Codex provider."""

from utils.codex_provider import CodexProvider

def main():
    print("Initializing Codex provider...")
    p = CodexProvider()
    print(f"Available: {p.is_available()}")

    if p.is_available():
        print("Sending test request...")
        r = p.infer('analysis', 'Say hello and confirm you are working.')
        print(f"Response: {r.text[:200] if r.text else 'None'}")
        print(f"Success: {r.success}")
        print(f"Model: {r.model}")
    else:
        print("FCC server not reachable - check if fcc-server is running!")

if __name__ == "__main__":
    main()