"""Inject reproducible build identity macros into PlatformIO builds."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

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

def git_status(repository: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


project_dir = Path(env.subst("$PROJECT_DIR"))
repository = project_dir.parent
short_sha = (git_output(repository, "rev-parse", "--short=7", "HEAD") or "unknown")[:7]
status = git_status(repository)

if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
    provenance_code = 3  # CI
elif short_sha == "unknown" or status is None:
    provenance_code = 0  # unknown/local without Git metadata
elif status:
    provenance_code = 2  # dirty local tree
else:
    provenance_code = 1  # clean local tree

env.Append(
    CPPDEFINES=[
        ("BUILD_GIT_SHA", env.StringifyMacro(short_sha)),
        ("BUILD_PROVENANCE_CODE", provenance_code),
        ("BUILD_PP16_PROFILE_REVISION", env.StringifyMacro("T006B-r1")),
    ]
)
print(
    "Build identity: "
    f"git={short_sha} provenance={provenance_code} profile=T006B-r1"
)
