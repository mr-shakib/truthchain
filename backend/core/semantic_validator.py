"""
Semantic Validator
==================
Detects contradictions between AI output and the context it was given,
using sentence-transformers cosine similarity.

Model: all-MiniLM-L6-v2 — 80 MB, CPU-only, ~5 ms per call.
No external API keys required. Loaded once as a singleton.

Usage (via rule_engine):
    {
        "type": "semantic",
        "output_field": "recommendation",
        "context_field": "patient_history",
        "min_alignment": 0.5,
        "severity": "error"
    }

The 'output_field' is looked up in the AI output dict.
The 'context_field' is looked up in the validation context dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SemanticResult:
    """Result of a single semantic alignment check."""
    score: float               # cosine similarity, 0.0–1.0
    is_contradiction: bool     # True when score < min_alignment
    explanation: str           # human-readable description
    output_text: str
    context_text: str
    threshold: float


class SemanticValidator:
    """
    Singleton wrapper around sentence-transformers.

    The model is loaded lazily on the first call so startup cost is
    incurred only when a semantic rule is actually used.
    """

    _instance: Optional[SemanticValidator] = None
    _model = None

    def __new__(cls) -> SemanticValidator:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # Internal model access
    # ------------------------------------------------------------------

    def _get_model(self):
        """Load the model once and cache it for the lifetime of the process."""
        if SemanticValidator._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                SemanticValidator._model = SentenceTransformer("all-MiniLM-L6-v2")
                print("[SemanticValidator] Model loaded: all-MiniLM-L6-v2")
            except Exception as exc:
                raise RuntimeError(
                    "sentence-transformers is required for semantic validation. "
                    "Install it with: pip install sentence-transformers"
                ) from exc
        return SemanticValidator._model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_alignment(
        self,
        output_text: str,
        context_text: str,
        min_alignment: float = 0.5,
    ) -> SemanticResult:
        """
        Compute cosine similarity between AI output and reference context.

        Parameters
        ----------
        output_text:    The AI-generated text to evaluate.
        context_text:   The reference/context text to compare against.
        min_alignment:  Minimum acceptable cosine similarity.
                        Below this threshold the pair is flagged as a
                        potential contradiction (default 0.5).

        Returns
        -------
        SemanticResult
        """
        from sentence_transformers import util

        model = self._get_model()

        emb_output = model.encode(str(output_text), convert_to_tensor=True)
        emb_context = model.encode(str(context_text), convert_to_tensor=True)
        score = float(util.cos_sim(emb_output, emb_context))
        # Clamp to [0, 1] — cos_sim can be slightly negative for opposite meanings
        score = max(0.0, min(1.0, score))

        is_contradiction = score < min_alignment

        if score >= 0.7:
            label = "strongly aligned"
        elif score >= min_alignment:
            label = "sufficiently aligned"
        elif score >= 0.3:
            label = "weakly aligned — possible semantic mismatch"
        else:
            label = "contradicted — output opposes the context"

        explanation = (
            f"Semantic alignment score: {score:.4f} ({label}). "
            f"Minimum required: {min_alignment}."
        )

        return SemanticResult(
            score=round(score, 4),
            is_contradiction=is_contradiction,
            explanation=explanation,
            output_text=str(output_text),
            context_text=str(context_text),
            threshold=min_alignment,
        )
