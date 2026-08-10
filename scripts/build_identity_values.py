"""Pure build identity normalization and provenance selection helpers."""

from __future__ import annotations

UNKNOWN_SHA = "unknown"
GIT_SHA_WIDTH = 7
PP16_PROFILE_REVISION = "T008F-r1"
IDENTITY_VALUE_FILENAME = "build_identity.txt"


def format_identity_values(
    *,
    git_sha: str,
    provenance_code: int,
    profile_revision: str,
) -> str:
    """Serialize the values injected into one deterministic build."""
    return (
        f"git_sha={git_sha}\n"
        f"provenance_code={provenance_code}\n"
        f"profile_revision={profile_revision}\n"
    )


def parse_identity_values(value: str) -> tuple[str, int, str]:
    """Parse the deterministic identity file emitted by the pre-stage."""
    fields: dict[str, str] = {}
    for line in value.splitlines():
        key, separator, field_value = line.partition("=")
        if not separator or not key or key in fields:
            raise ValueError("build identity contains malformed or duplicate fields")
        fields[key] = field_value
    try:
        git_sha = fields["git_sha"]
        provenance_code = int(fields["provenance_code"])
        profile_revision = fields["profile_revision"]
    except (KeyError, ValueError) as exc:
        raise ValueError("build identity is missing required fields") from exc
    if provenance_code not in (0, 1, 2, 3):
        raise ValueError(f"build identity has invalid provenance code {provenance_code}")
    return git_sha, provenance_code, profile_revision


def _validate_expected_sha(expected_git_sha: str) -> bytes:
    if not isinstance(expected_git_sha, str):
        raise ValueError("expected Git SHA must be exactly seven characters")
    if expected_git_sha == UNKNOWN_SHA or len(expected_git_sha) != GIT_SHA_WIDTH:
        raise ValueError(
            "expected Git SHA must be an exact seven-character value; "
            f"got {expected_git_sha!r}"
        )
    try:
        return expected_git_sha.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("expected Git SHA must contain ASCII characters") from exc


def _validate_expected_profile(expected_profile_revision: str) -> bytes:
    if not isinstance(expected_profile_revision, str) or not expected_profile_revision.strip():
        raise ValueError(
            "expected PP16 profile revision is missing; "
            "provide the profile compiled into the firmware"
        )
    try:
        return expected_profile_revision.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("expected PP16 profile revision must be ASCII") from exc


def _contains_identity_token(image: bytes, token: bytes, *, sha: bool) -> bool:
    """Find a token without accepting a longer adjacent SHA value."""
    offset = image.find(token)
    while offset >= 0:
        if sha:
            before = image[offset - 1 : offset]
            after = image[offset + len(token) : offset + len(token) + 1]
            hexadecimal = b"0123456789abcdefABCDEF"
            if before and before[0] in hexadecimal:
                offset = image.find(token, offset + 1)
                continue
            if after and after[0] in hexadecimal:
                offset = image.find(token, offset + 1)
                continue
        return True
    return False


def assert_firmware_identity(
    image: bytes,
    expected_git_sha: str,
    expected_profile_revision: str,
) -> None:
    """Reject an artifact that does not contain the current build identity."""
    expected_sha = _validate_expected_sha(expected_git_sha)
    expected_profile = _validate_expected_profile(expected_profile_revision)
    if not isinstance(image, bytes) or not image:
        raise ValueError("firmware artifact is empty; rebuild the application binary")
    if not _contains_identity_token(image, expected_sha, sha=True):
        raise ValueError(
            "firmware artifact is missing the expected Git SHA "
            f"{expected_git_sha!r}; rebuild to avoid accepting stale output"
        )
    if not _contains_identity_token(image, expected_profile, sha=False):
        raise ValueError(
            "firmware artifact is missing the expected PP16 profile revision "
            f"{expected_profile_revision!r}; rebuild with the current profile"
        )


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
