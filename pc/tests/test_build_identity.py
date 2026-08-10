from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from scripts.build_identity_values import (
    assert_firmware_identity,
    normalize_git_sha,
    select_provenance,
)


def test_normalize_git_sha_keeps_exact_wire_width() -> None:
    assert normalize_git_sha("abcdef012345") == "abcdef0"
    assert normalize_git_sha("1234567") == "1234567"


def test_normalize_git_sha_falls_back_without_git_metadata() -> None:
    assert normalize_git_sha(None) == "unknown"
    assert normalize_git_sha(" ") == "unknown"


def test_select_provenance_distinguishes_clean_dirty_unknown_and_ci() -> None:
    assert (
        select_provenance(
            github_actions=False,
            short_sha="abcdef0",
            status_ok=True,
            status_text="",
        )
        == 1
    )
    assert (
        select_provenance(
            github_actions=False,
            short_sha="abcdef0",
            status_ok=True,
            status_text=" M file",
        )
        == 2
    )
    assert (
        select_provenance(
            github_actions=False,
            short_sha="unknown",
            status_ok=True,
            status_text="",
        )
        == 0
    )
    assert (
        select_provenance(
            github_actions=False,
            short_sha="abcdef0",
            status_ok=False,
            status_text="",
        )
        == 0
    )
    assert (
        select_provenance(
            github_actions=True,
            short_sha="abcdef0",
            status_ok=True,
            status_text=" M file",
        )
        == 3
    )


def test_assert_firmware_identity_accepts_matching_sha_and_profile() -> None:
    image = b"\xe9\x01\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00abc1234\x00\x00\x00\x00T008F-r1"

    assert_firmware_identity(image, "abc1234", "T008F-r1")


@pytest.mark.parametrize(
    ("image", "expected_sha"),
    [
        (
            b"\xe9\x01\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00deadbee\x00\x00\x00\x00T008F-r1",
            "abc1234",
        ),
        (
            b"\xe9\x01\x02\x03"
            b"\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00"
            b"T008F-r1",
            "abc1234",
        ),
    ],
    ids=["stale-sha", "missing-sha"],
)
def test_assert_firmware_identity_rejects_stale_or_missing_sha(
    image: bytes, expected_sha: str
) -> None:
    with pytest.raises(ValueError):
        assert_firmware_identity(image, expected_sha, "T008F-r1")


def test_assert_firmware_identity_rejects_missing_profile() -> None:
    image = b"\xe9\x01\x02\x03\x00\x00\x00\x00\x00\x00\x00\x00abc1234\x00\x00\x00\x00T008F-r0"

    with pytest.raises(ValueError):
        assert_firmware_identity(image, "abc1234", "T008F-r1")


@pytest.mark.parametrize("expected_sha", ["abc123", "abc12345"])
def test_assert_firmware_identity_rejects_non_seven_character_sha(
    expected_sha: str,
) -> None:
    image = b"\xe9\x01\x02\x03abc1234T008F-r1"

    with pytest.raises(ValueError):
        assert_firmware_identity(image, expected_sha, "T008F-r1")
