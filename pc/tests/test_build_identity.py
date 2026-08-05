from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from scripts.build_identity_values import normalize_git_sha, select_provenance


def test_normalize_git_sha_keeps_exact_wire_width() -> None:
    assert normalize_git_sha("abcdef012345") == "abcdef0"
    assert normalize_git_sha("1234567") == "1234567"


def test_normalize_git_sha_falls_back_without_git_metadata() -> None:
    assert normalize_git_sha(None) == "unknown"
    assert normalize_git_sha(" ") == "unknown"


def test_select_provenance_distinguishes_clean_dirty_unknown_and_ci() -> None:
    assert (
        select_provenance(github_actions=False, short_sha="abcdef0", status_ok=True, status_text="")
        == 1
    )
    assert (
        select_provenance(
            github_actions=False, short_sha="abcdef0", status_ok=True, status_text=" M file"
        )
        == 2
    )
    assert (
        select_provenance(github_actions=False, short_sha="unknown", status_ok=True, status_text="")
        == 0
    )
    assert (
        select_provenance(
            github_actions=False, short_sha="abcdef0", status_ok=False, status_text=""
        )
        == 0
    )
    assert (
        select_provenance(
            github_actions=True, short_sha="abcdef0", status_ok=True, status_text=" M file"
        )
        == 3
    )
