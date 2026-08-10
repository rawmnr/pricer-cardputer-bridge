"""Inject reproducible build identity macros during PlatformIO pre-build."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from build_identity_values import (
    IDENTITY_VALUE_FILENAME,
    PP16_PROFILE_REVISION,
    format_identity_values,
    normalize_git_sha,
    select_provenance,
)

Import("env")


def git_output(repository: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def git_status(repository: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False, ""
    return True, result.stdout.strip()


def write_identity_value(
    identity_path: Path,
    *,
    git_sha: str,
    provenance_code: int,
    profile_revision: str,
) -> None:
    """Persist the values used by this build as a deterministic dependency."""
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    value = format_identity_values(
        git_sha=git_sha,
        provenance_code=provenance_code,
        profile_revision=profile_revision,
    )
    if identity_path.exists() and identity_path.read_text(encoding="ascii") == value:
        return
    identity_path.write_text(value, encoding="ascii", newline="\n")


project_dir = Path(env.subst("$PROJECT_DIR"))
repository = project_dir.parent
short_sha = normalize_git_sha(git_output(repository, "rev-parse", "--short=7", "HEAD"))
status_ok, status = git_status(repository)
provenance_code = select_provenance(
    github_actions=os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    short_sha=short_sha,
    status_ok=status_ok,
    status_text=status,
)

env.Append(
    CPPDEFINES=[
        ("BUILD_GIT_SHA", env.StringifyMacro(short_sha)),
        ("BUILD_PROVENANCE_CODE", provenance_code),
        ("BUILD_PP16_PROFILE_REVISION", env.StringifyMacro(PP16_PROFILE_REVISION)),
    ]
)

identity_path = Path(env.subst("$BUILD_DIR")) / IDENTITY_VALUE_FILENAME
write_identity_value(
    identity_path,
    git_sha=short_sha,
    provenance_code=provenance_code,
    profile_revision=PP16_PROFILE_REVISION,
)
print(
    "Build identity: "
    f"git={short_sha} provenance={provenance_code} profile={PP16_PROFILE_REVISION}"
)
