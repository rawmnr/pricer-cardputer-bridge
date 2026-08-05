"""Pure build identity normalization and provenance selection helpers."""

from __future__ import annotations

UNKNOWN_SHA = "unknown"


def normalize_git_sha(value: str | None) -> str:
    """Return the exact seven-character wire/display SHA fallback."""
    normalized = (value or "").strip()
    return normalized[:7] if normalized else UNKNOWN_SHA


def select_provenance(
    *,
    github_actions: bool,
    short_sha: str,
    status_ok: bool,
    status_text: str,
) -> int:
    """Return 0 unknown, 1 clean, 2 dirty, or 3 CI."""
    if github_actions:
        return 3
    if short_sha == UNKNOWN_SHA or not status_ok:
        return 0
    return 2 if status_text else 1
