"""
Quick Tavily test — current weather in Dhaka, Bangladesh
Run: .\venv\Scripts\python.exe test_dhaka_weather.py
"""
import sys, asyncio
sys.path.insert(0, ".")

from backend.core.web_verifier import WebVerifier
from backend.config.settings import settings

TAVILY_KEY = settings.TAVILY_API_KEY

async def main():
    verifier = WebVerifier(api_key=TAVILY_KEY)

    # --- Raw Tavily search: get live weather snippets ---
    print("Searching Tavily for: 'current weather Dhaka Bangladesh today'\n")
    raw = await verifier._tavily_search(
        query="current weather Dhaka Bangladesh today",
        search_depth="advanced",
        max_results=5,
    )

    print(f"Results returned: {len(raw)}\n")
    for i, r in enumerate(raw, 1):
        print(f"[{i}] {r.get('title', 'no title')}")
        print(f"    URL     : {r.get('url', '')}")
        print(f"    Score   : {r.get('score', 0):.3f}")
        print(f"    Snippet : {(r.get('content') or r.get('snippet', ''))[:300]}")
        print()

    # --- Now run full verify() to score them semantically ---
    print("=" * 60)
    print("WebVerifier.verify() — full pipeline\n")
    claim = "Current weather in Dhaka, Bangladesh is hot and humid with temperatures around 28°C"
    result = await verifier.verify(
        claim=claim,
        search_depth="advanced",
        max_results=5,
    )

    print(f"Claim      : {claim}")
    print(f"Confidence : {result.web_confidence}")
    print(f"Verdict    : {result.verdict}")
    print()
    print("Top sources by semantic score:")
    for s in result.sources[:5]:
        print(f"  [{s.semantic_score:.3f}] {s.title[:65]}")
        print(f"          {s.url[:80]}")
        print(f"          {s.snippet[:200]}")
        print()

asyncio.run(main())
