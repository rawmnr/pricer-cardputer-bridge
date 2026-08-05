"""Inject reproducible build identity macros into PlatformIO builds."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from build_identity_values import normalize_git_sha, select_provenance

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
        ("BUILD_PP16_PROFILE_REVISION", env.StringifyMacro("T008C-r1")),
    ]
)
print(
    "Build identity: "
    f"git={short_sha} provenance={provenance_code} profile=T008C-r1"
)
