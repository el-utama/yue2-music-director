"""Extract song job IDs from YuE2 MCP responses without confusing library song IDs.

No network access here. A missing or ambiguous receipt must never trigger a retry.
"""
from __future__ import annotations
import json
from typing import Any


class AmbiguousJobReceipt(ValueError):
    """Inconsistent job IDs returned by an MCP server."""


def _looks_like_job(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    return ('status' in obj or 'phase' in obj) and any(
        key in obj for key in ('phase', 'tracks', 'tracks_asked', 'songs')
    )


def _candidate(obj: Any) -> str | None:
    if not isinstance(obj, dict):
        return None
    for key in ('job_id', 'jobId'):
        value = obj.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    if _looks_like_job(obj):
        value = obj.get('id')
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    return None


def extract_song_job_id(response: Any) -> str | None:
    """Recognize the live structuredContent.id and text(json).id envelopes.

    Accepts an already-decoded MCP response or bare job object. If the
    structured and textual representations disagree, fails closed.
    """
    if not isinstance(response, dict):
        return None
    candidates: set[str] = set()
    values: list[Any] = [response, response.get('structuredContent')]
    for item in response.get('content', []):
        if not isinstance(item, dict) or item.get('type') != 'text':
            continue
        try:
            values.append(json.loads(item.get('text', '')))
        except (TypeError, ValueError):
            continue
    for obj in values:
        if isinstance(obj, dict):
            values_for_check = [obj, obj.get('job')]
        elif isinstance(obj, list):
            values_for_check = obj
        else:
            values_for_check = []
        for item in values_for_check:
            candidate = _candidate(item)
            if candidate:
                candidates.add(candidate)
    if len(candidates) > 1:
        raise AmbiguousJobReceipt('MCP response contains conflicting job identifiers')
    return next(iter(candidates), None)
