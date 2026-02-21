"""
External Reference Validator for TruthChain
============================================
A connector registry that lets any async function act as an external truth
source for the ``type: external_ref`` rule.

Usage — registering a custom connector
---------------------------------------
    from backend.core.external_reference import (
        ExternalReferenceValidator, ConnectorResult
    )

    async def stripe_customer_exists(value: str, **params) -> ConnectorResult:
        import httpx
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"https://api.stripe.com/v1/customers/{value}",
                auth=(STRIPE_KEY, ""),
            )
            return ConnectorResult(
                exists=r.status_code == 200,
                detail=f"Stripe HTTP {r.status_code}",
            )

    ExternalReferenceValidator.register("stripe_customer", stripe_customer_exists)

Pre-built connectors (no API key required)
------------------------------------------
- ``http_get_200``         — GETs any URL; succeeds when HTTP 200
- ``http_json_field``      — GETs URL, reads a dot-path JSON field, compares to expected
- ``aladhan_fajr_in_range``— Calls Aladhan public prayer-times API; checks a claimed
                             Sehri/Fajr time is within ``tolerance_minutes`` of the
                             official Fajr time for a given city.

Connector contract
------------------
Every connector must be an async callable with the signature:

    async def connector(value: Any, **params) -> ConnectorResult

``value`` is whatever the output field contains (string, number, etc.).
``params`` come from the rule's ``params`` dict.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import re

import httpx


# ──────────────────────────────────────────────────────────────────────────────
# Public data types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ConnectorResult:
    """
    Result returned by every external-reference connector.

    Attributes:
        exists      True when the external check passes (value is valid / found).
        detail      Human-readable explanation of the outcome.
        latency_ms  Round-trip time in milliseconds (set automatically).
        raw         Optional raw response from the external API.
    """
    exists: bool
    detail: str = ""
    latency_ms: int = 0
    raw: Any = field(default=None, repr=False)


# ──────────────────────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────────────────────

class ExternalReferenceValidator:
    """
    Singleton-style registry of named async connector functions.

    Register connectors at app start-up and reuse throughout the process.
    Thread-safe for reads; ``register()`` is typically called only at import time.
    """

    _connectors: Dict[str, Callable] = {}

    # ── registration ──────────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str, connector: Callable) -> None:
        """
        Register a connector under *name*.

        Args:
            name:      Identifier used in ``rule["connector"]`` (e.g. ``"stripe_customer"``).
            connector: An ``async def fn(value, **params) -> ConnectorResult``.
        """
        if not callable(connector):
            raise TypeError(f"Connector '{name}' must be callable, got {type(connector)}")
        cls._connectors[name] = connector

    @classmethod
    def registered_names(cls) -> list[str]:
        """Return a sorted list of all registered connector names."""
        return sorted(cls._connectors.keys())

    # ── invocation ────────────────────────────────────────────────────────────

    @classmethod
    async def check(
        cls,
        connector_name: str,
        value: Any,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> ConnectorResult:
        """
        Call the named connector with *value* and optional *params*.

        Measures latency automatically. Wraps network/timeout errors into a
        ``ConnectorResult(exists=False)`` so the caller never sees raw exceptions.

        Args:
            connector_name: Must match a previously registered name.
            value:          The output-field value to verify.
            params:         Extra keyword arguments forwarded to the connector.
            timeout:        Maximum seconds to wait (default 10 s).

        Returns:
            ConnectorResult — never raises.

        Raises:
            KeyError: If *connector_name* is not registered.
        """
        if connector_name not in cls._connectors:
            available = cls.registered_names()
            raise KeyError(
                f"Connector '{connector_name}' is not registered. "
                f"Available: {available}"
            )

        connector = cls._connectors[connector_name]
        params = params or {}
        t0 = time.monotonic()

        try:
            result: ConnectorResult = await connector(value, **params)
        except httpx.TimeoutException:
            result = ConnectorResult(
                exists=False,
                detail=f"Connector '{connector_name}' timed out after {timeout}s",
            )
        except Exception as exc:  # noqa: BLE001
            result = ConnectorResult(
                exists=False,
                detail=f"Connector '{connector_name}' error: {exc}",
            )

        result.latency_ms = int((time.monotonic() - t0) * 1000)
        return result


# ──────────────────────────────────────────────────────────────────────────────
# Pre-built connectors
# ──────────────────────────────────────────────────────────────────────────────

async def _connector_http_get_200(value: str, **params) -> ConnectorResult:
    """
    GETs *value* (which must be a URL) and checks whether the server responds
    with HTTP 200 OK.

    Params: none required.

    Example rule::

        {"type": "external_ref", "field": "source_url",
         "connector": "http_get_200", "severity": "error"}
    """
    url = str(value).strip()
    timeout = float(params.get("timeout", 8.0))

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url)

    ok = r.status_code == 200
    return ConnectorResult(
        exists=ok,
        detail=f"GET {url} → HTTP {r.status_code}",
        raw={"status_code": r.status_code},
    )


async def _connector_http_json_field(value: Any, **params) -> ConnectorResult:
    """
    GETs a URL from *params*, extracts a dot-path field from the JSON body,
    and checks whether the field value matches *expected* (if supplied) or
    simply exists (if *expected* is not set).

    Required params:
        url        URL to GET (may include query params).
        json_path  Dot-separated path into the JSON response
                   (e.g. ``"data.timings.Fajr"``).

    Optional params:
        expected   Value to compare the field against (string comparison).
        timeout    HTTP timeout in seconds (default 8).

    Example rule::

        {
          "type": "external_ref",
          "field": "fajr_time",
          "connector": "http_json_field",
          "params": {
            "url": "https://api.aladhan.com/v1/timingsByCity?city=Dhaka&country=Bangladesh",
            "json_path": "data.timings.Fajr"
          },
          "severity": "warning"
        }
    """
    url = str(params.get("url", "")).strip()
    json_path = str(params.get("json_path", "")).strip()
    expected = params.get("expected")
    timeout = float(params.get("timeout", 8.0))

    if not url or not json_path:
        return ConnectorResult(
            exists=False,
            detail="http_json_field requires 'url' and 'json_path' params",
        )

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url)

    if r.status_code != 200:
        return ConnectorResult(
            exists=False,
            detail=f"GET {url} → HTTP {r.status_code} (expected 200)",
            raw={"status_code": r.status_code},
        )

    # Walk the dot-path
    data = r.json()
    node: Any = data
    for key in json_path.split("."):
        if isinstance(node, dict):
            node = node.get(key)
        else:
            node = None
            break

    if node is None:
        return ConnectorResult(
            exists=False,
            detail=f"Field '{json_path}' not found in JSON response from {url}",
            raw=data,
        )

    field_str = str(node).strip()

    if expected is not None:
        match = field_str == str(expected).strip()
        return ConnectorResult(
            exists=match,
            detail=(
                f"Field '{json_path}' = '{field_str}' "
                + ("matches" if match else f"≠ expected '{expected}'")
            ),
            raw={"field": json_path, "found": field_str, "expected": expected},
        )

    return ConnectorResult(
        exists=True,
        detail=f"Field '{json_path}' = '{field_str}'",
        raw={"field": json_path, "found": field_str},
    )


def _parse_hhmm(time_str: str) -> Optional[int]:
    """Return minutes-since-midnight for 'HH:MM' strings, else None."""
    m = re.match(r"(\d{1,2}):(\d{2})", str(time_str).strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


async def _connector_aladhan_fajr_in_range(value: Any, **params) -> ConnectorResult:
    """
    Calls the free Aladhan prayer-times API (no API key required) and checks
    whether a claimed Fajr / Sehri-end time is within *tolerance_minutes* of
    the official Fajr time for the given city.

    Required params:
        city              City name (e.g. ``"Dhaka"``).
        country           Country name (e.g. ``"Bangladesh"``).

    Optional params:
        method         Aladhan calculation method (default ``1`` = University of Islamic Sciences, Karachi).
        tolerance_minutes  Allowed deviation in minutes (default ``15``).
        date           Date as ``"DD-MM-YYYY"`` (default: today per Aladhan).
        timeout        HTTP timeout (default 8 s).

    The *value* field should be a time string like ``"05:10"`` or ``"05:10 AM"``.

    Example rule::

        {
          "type": "external_ref",
          "field": "sehri_time",
          "connector": "aladhan_fajr_in_range",
          "params": {"city": "Dhaka", "country": "Bangladesh", "tolerance_minutes": 15},
          "severity": "error"
        }
    """
    city = str(params.get("city", "Dhaka"))
    country = str(params.get("country", "Bangladesh"))
    method = int(params.get("method", 1))
    tolerance = int(params.get("tolerance_minutes", 15))
    date_str = params.get("date")  # optional override — "DD-MM-YYYY"
    timeout = float(params.get("timeout", 8.0))

    # Build URL
    base = "https://api.aladhan.com/v1/timingsByCity"
    query = f"?city={city}&country={country}&method={method}"
    if date_str:
        query += f"&date={date_str}"
    url = base + query

    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url)

    if r.status_code != 200:
        return ConnectorResult(
            exists=False,
            detail=f"Aladhan API → HTTP {r.status_code}",
            raw={"status_code": r.status_code},
        )

    body = r.json()
    official_fajr_raw: Optional[str] = (
        body.get("data", {}).get("timings", {}).get("Fajr")
    )
    if official_fajr_raw is None:
        return ConnectorResult(
            exists=False,
            detail="Aladhan API response missing 'data.timings.Fajr'",
            raw=body,
        )

    # Strip timezone suffix like " (+06)" → "05:10"
    official_fajr_clean = re.sub(r"\s*\(.*?\)", "", official_fajr_raw).strip()
    official_mins = _parse_hhmm(official_fajr_clean)
    if official_mins is None:
        return ConnectorResult(
            exists=False,
            detail=f"Could not parse official Fajr time: '{official_fajr_raw}'",
        )

    claimed_mins = _parse_hhmm(str(value))
    if claimed_mins is None:
        return ConnectorResult(
            exists=False,
            detail=f"Could not parse claimed time: '{value}'",
        )

    diff = abs(claimed_mins - official_mins)
    within = diff <= tolerance

    claimed_fmt = f"{claimed_mins // 60:02d}:{claimed_mins % 60:02d}"
    official_fmt = f"{official_mins // 60:02d}:{official_mins % 60:02d}"

    return ConnectorResult(
        exists=within,
        detail=(
            f"Claimed Sehri/Fajr {claimed_fmt} vs official Aladhan Fajr "
            f"{official_fmt} ({city}) — diff {diff} min "
            + ("✓ within" if within else "✗ exceeds")
            + f" tolerance {tolerance} min"
        ),
        raw={
            "official_fajr": official_fajr_raw,
            "claimed": str(value),
            "diff_minutes": diff,
            "tolerance_minutes": tolerance,
            "city": city,
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Auto-register all pre-built connectors
# ──────────────────────────────────────────────────────────────────────────────

ExternalReferenceValidator.register("http_get_200",            _connector_http_get_200)
ExternalReferenceValidator.register("http_json_field",         _connector_http_json_field)
ExternalReferenceValidator.register("aladhan_fajr_in_range",   _connector_aladhan_fajr_in_range)
