"""Verify application identity after PlatformIO builders are available."""

from __future__ import annotations

from pathlib import Path

from build_identity_values import (
    IDENTITY_VALUE_FILENAME,
    assert_firmware_identity,
    parse_identity_values,
)

Import("env")


def _node_path(candidate: object) -> Path:
    get_abspath = getattr(candidate, "get_abspath", None)
    if callable(get_abspath):
        return Path(get_abspath())
    return Path(str(candidate))


def _candidate_paths(group: object) -> tuple[Path, ...]:
    if isinstance(group, (str, bytes, Path)):
        return (_node_path(group),)
    try:
        return tuple(_node_path(candidate) for candidate in group)  # type: ignore[union-attr]
    except TypeError:
        return (_node_path(group),)


def _artifact_path(target: object, source: object) -> Path:
    candidates = _candidate_paths(target) + _candidate_paths(source)
    for candidate in candidates:
        if candidate.suffix.lower() == ".bin":
            return candidate
    if candidates:
        return candidates[0]
    raise RuntimeError("PlatformIO did not provide a firmware artifact target")


def verify_artifact(
    target: object = None,
    source: object = None,
    env: object = None,
) -> None:
    """Reject an application binary that does not contain pre-stage identity."""
    del env
    artifact_path = _artifact_path(target, source)
    build_dir = artifact_path.parent
    identity_path = build_dir / IDENTITY_VALUE_FILENAME
    try:
        identity_text = identity_path.read_text(encoding="ascii")
        expected_git_sha, _provenance_code, expected_profile_revision = (
            parse_identity_values(identity_text)
        )
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            f"cannot read build identity {identity_path}: {exc}"
        ) from exc
    try:
        image = artifact_path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read firmware artifact {artifact_path}: {exc}") from exc
    try:
        assert_firmware_identity(
            image,
            expected_git_sha,
            expected_profile_revision,
        )
    except ValueError as exc:
        raise RuntimeError(
            f"firmware identity verification failed for {artifact_path}: {exc}"
        ) from exc
    print(
        "Verified firmware identity: "
        f"git={expected_git_sha} profile={expected_profile_revision}"
    )


build_dir = Path(env.subst("$BUILD_DIR"))
identity_path = build_dir / IDENTITY_VALUE_FILENAME
elf_target = env.subst("$BUILD_DIR/${PROGNAME}.elf")
bin_target = env.subst("$BUILD_DIR/${PROGNAME}.bin")
env.Depends(elf_target, str(identity_path))
env.Depends(bin_target, str(identity_path))
env.AddPostAction(bin_target, verify_artifact)
