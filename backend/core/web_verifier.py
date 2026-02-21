"""
Web Verifier
============
Verifies factual claims extracted from AI output by searching the web
via the Tavily API and scoring results using sentence-transformers
cosine similarity.

Tavily is purpose-built for LLM grounding:
  - Returns cleaned text snippets (no HTML)
  - Built-in relevance scoring
  - Async client
  - ~$20/month for typical usage

Sign up at https://app.tavily.com and set TAVILY_API_KEY in .env

Rule type:
    {
        "type": "web_verify",
        "field": "ai_response",           # field in output dict containing the claim
        "confidence_threshold": 0.7,       # below this → violation (default 0.7)
        "search_depth": "basic",           # "basic" (fast) or "advanced" (thorough)
        "max_results": 5,                  # Tavily results to fetch
        "severity": "error"
    }

Pipeline:
    claim text
       │
       ▼
    Tavily search (async) → top-N text snippets + source URLs
       │
       ▼
    SemanticValidator.check_alignment() per snippet (cosine sim)
       │
       ▼
    web_confidence = mean of top-3 semantic scores
       │
       ▼
    verdict = SUPPORTED | UNCERTAIN | CONTRADICTED
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class WebSource:
    """A single search result / evidence source."""
    url: str
    title: str
    snippet: str
    tavily_score: float   # Tavily's own relevance score (0–1)
    semantic_score: float  # our cosine similarity to the claim


@dataclass
class WebVerificationResult:
    """Complete result of a web-grounded fact-check."""
    claim: str
    query: str
    web_confidence: float              # 0.0 – 1.0 (our computed score)
    verdict: str                        # SUPPORTED | UNCERTAIN | CONTRADICTED
    sources: List[WebSource] = field(default_factory=list)
    error: Optional[str] = None        # set when Tavily call fails


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class WebVerifier:
    """
    Singleton-style web fact-checker using Tavily + sentence-transformers.

    Usage::

        verifier = WebVerifier(api_key="tvly-...")
        result = await verifier.verify("Apple Q4 2025 revenue was $85 billion")

        print(result.verdict)          # CONTRADICTED
        print(result.web_confidence)   # 0.24
        for src in result.sources:
            print(src.url, src.semantic_score)
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._sync_client = None       # TavilyClient (sync fallback)
        self._async_client = None      # AsyncTavilyClient (preferred)

    # ------------------------------------------------------------------
    # Tavily client initialisation (lazy, with async-first fallback)
    # ------------------------------------------------------------------

    def _get_sync_client(self):
        if self._sync_client is None:
            from tavily import TavilyClient
            self._sync_client = TavilyClient(api_key=self.api_key)
        return self._sync_client

    def _get_async_client(self):
        if self._async_client is None:
            try:
                from tavily import AsyncTavilyClient
                self._async_client = AsyncTavilyClient(api_key=self.api_key)
            except ImportError:
                # Older builds of tavily-python don't have AsyncTavilyClient
                self._async_client = None
        return self._async_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def verify(
        self,
        claim: str,
        search_depth: str = "basic",
        max_results: int = 5,
        supported_threshold: float = 0.65,
        contradicted_threshold: float = 0.30,
    ) -> WebVerificationResult:
        """
        Verify a factual claim against live web sources.

        Parameters
        ----------
        claim               : The text to fact-check (e.g. the AI output field value).
        search_depth        : "basic" (1–2 s) or "advanced" (3–5 s, more sources).
        max_results         : How many Tavily results to fetch (3–10 is reasonable).
        supported_threshold : Mean semantic score above which verdict = SUPPORTED.
        contradicted_threshold: Mean semantic score below which verdict = CONTRADICTED.

        Returns
        -------
        WebVerificationResult
        """
        try:
            raw_results = await self._tavily_search(
                query=claim,
                search_depth=search_depth,
                max_results=max_results,
            )
        except Exception as exc:
            return WebVerificationResult(
                claim=claim,
                query=claim,
                web_confidence=0.0,
                verdict="UNCERTAIN",
                error=f"Tavily search failed: {exc}",
            )

        if not raw_results:
            return WebVerificationResult(
                claim=claim,
                query=claim,
                web_confidence=0.0,
                verdict="UNCERTAIN",
                error="No search results returned.",
            )

        # Score each snippet against the claim
        sources = self._score_results(claim, raw_results)

        # web_confidence = mean of top-3 semantic scores
        scores = sorted([s.semantic_score for s in sources], reverse=True)
        top_scores = scores[:3] if len(scores) >= 3 else scores
        web_confidence = round(sum(top_scores) / len(top_scores), 4)

        if web_confidence >= supported_threshold:
            verdict = "SUPPORTED"
        elif web_confidence <= contradicted_threshold:
            verdict = "CONTRADICTED"
        else:
            verdict = "UNCERTAIN"

        return WebVerificationResult(
            claim=claim,
            query=claim,
            web_confidence=web_confidence,
            verdict=verdict,
            sources=sources,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _tavily_search(
        self,
        query: str,
        search_depth: str,
        max_results: int,
    ) -> list:
        """
        Call Tavily, returning the raw list of result dicts.
        Uses AsyncTavilyClient if available, otherwise runs the sync
        client in a thread-pool executor to remain non-blocking.
        """
        async_client = self._get_async_client()
        if async_client is not None:
            response = await async_client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
            )
        else:
            # Fallback: run sync call in executor
            loop = asyncio.get_event_loop()
            sync_client = self._get_sync_client()
            response = await loop.run_in_executor(
                None,
                lambda: sync_client.search(
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results,
                ),
            )

        return response.get("results", []) if isinstance(response, dict) else []

    def _score_results(
        self,
        claim: str,
        raw_results: list,
    ) -> List[WebSource]:
        """
        Compute cosine similarity between the claim and each snippet,
        then sort by semantic_score descending.
        """
        from .semantic_validator import SemanticValidator

        sv = SemanticValidator()
        sources: List[WebSource] = []

        for item in raw_results:
            snippet = item.get("content", "") or item.get("snippet", "")
            if not snippet:
                continue
            # Cosine similarity: claim vs snippet
            sem_result = sv.check_alignment(
                output_text=claim,
                context_text=snippet,
                min_alignment=0.0,   # we only want the score, not a violation
            )
            sources.append(WebSource(
                url=item.get("url", ""),
                title=item.get("title", ""),
                snippet=snippet[:400],
                tavily_score=float(item.get("score", 0.0)),
                semantic_score=sem_result.score,
            ))

        sources.sort(key=lambda s: s.semantic_score, reverse=True)
        return sources
