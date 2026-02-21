"""
ML Anomaly Detector
===================
Per-organisation IsolationForest model that learns from a customer's own
validation history and flags statistically unusual AI outputs.

Why IsolationForest?
- Unsupervised — no labelled "bad" examples needed
- Fast at inference (~1 ms per sample after training)
- Works well on tabular numeric features (the kind TruthChain validates)
- `sklearn` is already in requirements

Rule type::

    {
        "type": "anomaly_ml",
        "name": "hours_anomaly",
        "fields": ["hours", "total_cost", "line_items"],   # numeric fields to watch
        "min_samples": 50,          # don't flag until we have enough history
        "contamination": 0.05,      # expected fraction of anomalies (default 5%)
        "severity": "warning"
    }

Training lifecycle
------------------
The model is trained lazily on first use per org once `min_samples` records
are available. Training is done inline (fast — <100 ms for <10k samples).
Models are cached in memory for the process lifetime.

Call `MLAnomalyDetector.train_for_org(org_id, samples, fields)` explicitly
to pre-train, or let the rule engine trigger it automatically.

Serialisation
-------------
Models are optionally persisted to disk via joblib for survival across
process restarts. Set `model_dir` to a writable path (defaults to the
system temp dir). Pass `model_dir=None` to keep everything in-memory only.
"""

from __future__ import annotations

import os
import tempfile
import logging
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class MLAnomalyScore:
    """Result of IsolationForest inference for a single sample."""
    org_id: str
    is_anomaly: bool
    raw_score: float          # IF decision_function score: negative = anomaly
    severity: str             # "warning" or "error"
    fields_used: List[str]
    reason: str


@dataclass
class TrainingResult:
    """Outcome of a train() call."""
    org_id: str
    success: bool
    n_samples: int
    fields: List[str]
    message: str


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class MLAnomalyDetector:
    """
    Manages one IsolationForest model per organisation.

    Thread-safety: models are cached in a dict; training overwrites atomically,
    which is safe for async contexts since Python's GIL protects dict writes.
    """

    MIN_SAMPLES_DEFAULT = 50

    def __init__(self, model_dir: Optional[str] = "default") -> None:
        """
        Parameters
        ----------
        model_dir:
            Directory to persist trained models via joblib.
            Pass ``None`` to use memory-only mode (models lost on restart).
            Pass ``"default"`` to use ``<tmpdir>/truthchain_ml_models/``.
        """
        if model_dir == "default":
            model_dir = os.path.join(tempfile.gettempdir(), "truthchain_ml_models")
        self._model_dir = model_dir
        if self._model_dir:
            os.makedirs(self._model_dir, exist_ok=True)

        # org_id → {"model": IsolationForest, "fields": [...], "n_samples": int}
        self._models: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_trained(self, org_id: str) -> bool:
        return org_id in self._models and self._models[org_id].get("model") is not None

    def train(
        self,
        org_id: str,
        samples: List[Dict[str, Any]],
        fields: List[str],
        contamination: float = 0.05,
    ) -> TrainingResult:
        """
        Train (or retrain) the IsolationForest for an org.

        Parameters
        ----------
        org_id:       Organisation identifier.
        samples:      List of output dicts (historical validation records).
        fields:       Which numeric fields to include as features.
        contamination:Expected fraction of anomalies in the training data.

        Returns
        -------
        TrainingResult
        """
        from sklearn.ensemble import IsolationForest  # lazy import

        X = self._vectorize(samples, fields)
        if X is None or len(X) < 2:
            return TrainingResult(
                org_id=org_id,
                success=False,
                n_samples=len(samples),
                fields=fields,
                message=f"Not enough numeric samples to train ({len(samples)} rows). Need >= 2.",
            )

        try:
            model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
            )
            model.fit(X)
            self._models[org_id] = {
                "model": model,
                "fields": fields,
                "n_samples": len(X),
                "contamination": contamination,
            }
            self._save(org_id)
            logger.info(
                f"[MLAnomalyDetector] Trained org={org_id} "
                f"n={len(X)} fields={fields}"
            )
            return TrainingResult(
                org_id=org_id,
                success=True,
                n_samples=len(X),
                fields=fields,
                message=f"IsolationForest trained on {len(X)} samples, {len(fields)} features.",
            )
        except Exception as exc:
            return TrainingResult(
                org_id=org_id,
                success=False,
                n_samples=len(samples),
                fields=fields,
                message=f"Training failed: {exc}",
            )

    def score(
        self,
        org_id: str,
        sample: Dict[str, Any],
        fields: List[str],
        severity: str = "warning",
    ) -> MLAnomalyScore:
        """
        Score a single output sample against the trained model.

        Returns
        -------
        MLAnomalyScore  (is_anomaly=False if model not yet trained)
        """
        if not self.is_trained(org_id):
            # Try loading from disk before giving up
            if not self._load(org_id):
                return MLAnomalyScore(
                    org_id=org_id,
                    is_anomaly=False,
                    raw_score=0.0,
                    severity=severity,
                    fields_used=fields,
                    reason="Model not trained yet — need more historical data.",
                )

        stored = self._models[org_id]
        trained_fields = stored.get("fields", fields)

        X = self._vectorize([sample], trained_fields)
        if X is None:
            return MLAnomalyScore(
                org_id=org_id,
                is_anomaly=False,
                raw_score=0.0,
                severity=severity,
                fields_used=trained_fields,
                reason="Could not extract numeric features from sample.",
            )

        model = stored["model"]
        raw = float(model.decision_function(X)[0])
        # IsolationForest: negative score → anomaly, positive → normal
        is_anomaly = raw < 0

        reason = (
            f"IsolationForest score: {raw:.4f} — "
            + ("ANOMALY detected (score < 0)" if is_anomaly else "normal (score >= 0)")
            + f". Fields: {trained_fields}."
        )

        return MLAnomalyScore(
            org_id=org_id,
            is_anomaly=is_anomaly,
            raw_score=round(raw, 4),
            severity=severity,
            fields_used=trained_fields,
            reason=reason,
        )

    def train_from_validation_logs(
        self,
        org_id: str,
        logs: List[Dict[str, Any]],
        fields: List[str],
        contamination: float = 0.05,
    ) -> TrainingResult:
        """
        Convenience wrapper: train directly from a list of stored validation
        log output dicts (as returned by the ValidationLog ORM model).
        Same as ``train()`` but named for clarity at the call site.
        """
        return self.train(org_id, logs, fields, contamination)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _vectorize(
        self,
        samples: List[Dict[str, Any]],
        fields: List[str],
    ) -> Optional[np.ndarray]:
        """
        Convert a list of output dicts into a 2-D numpy feature matrix.

        Non-numeric or missing values are replaced with the column mean
        (or 0 if the entire column is missing).
        """
        rows = []
        for sample in samples:
            row = []
            for f in fields:
                val = self._get_nested(sample, f)
                try:
                    row.append(float(val) if val is not None else np.nan)
                except (ValueError, TypeError):
                    row.append(np.nan)
            rows.append(row)

        if not rows:
            return None

        X = np.array(rows, dtype=float)

        # Replace NaN with column mean (or 0)
        col_means = np.nanmean(X, axis=0)
        col_means = np.where(np.isnan(col_means), 0.0, col_means)
        inds = np.where(np.isnan(X))
        X[inds] = np.take(col_means, inds[1])

        return X

    def _get_nested(self, obj: Dict, path: str) -> Any:
        """Dot-notation nested dict access."""
        keys = path.split(".")
        val = obj
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val

    def _model_path(self, org_id: str) -> Optional[str]:
        if not self._model_dir:
            return None
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in org_id)
        return os.path.join(self._model_dir, f"if_{safe}.joblib")

    def _save(self, org_id: str) -> None:
        path = self._model_path(org_id)
        if not path:
            return
        try:
            import joblib
            joblib.dump(self._models[org_id], path)
        except Exception as exc:
            logger.warning(f"[MLAnomalyDetector] Could not save model for {org_id}: {exc}")

    def _load(self, org_id: str) -> bool:
        path = self._model_path(org_id)
        if not path or not os.path.exists(path):
            return False
        try:
            import joblib
            self._models[org_id] = joblib.load(path)
            logger.info(f"[MLAnomalyDetector] Loaded model for org={org_id} from {path}")
            return True
        except Exception as exc:
            logger.warning(f"[MLAnomalyDetector] Could not load model for {org_id}: {exc}")
            return False


# ---------------------------------------------------------------------------
# Module-level singleton (used by rule_engine)
# ---------------------------------------------------------------------------

_detector: Optional[MLAnomalyDetector] = None


def get_ml_anomaly_detector() -> MLAnomalyDetector:
    """Return the process-level singleton, initialising it on first call."""
    global _detector
    if _detector is None:
        _detector = MLAnomalyDetector()
    return _detector
