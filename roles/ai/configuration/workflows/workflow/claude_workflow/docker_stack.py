"""Host-side Docker test stack: guard, worktree preparation and command builders.

Claude never gets Docker access. The host starts the compose stack from the ticket's
worktree and runs host commands, but only after `guard_violations` confirms that no
Docker-related file differs from the base commit.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path

from claude_workflow.config import DEFAULT_PROTECTED_PATHS, DockerConfig
from claude_workflow.git_host import ignored_paths, touched_paths

# Extra seconds for `up` to build images before `--wait-timeout` starts counting.
UP_BUILD_HEADROOM = 600


def _under(path: str, entry: str) -> bool:
    return path == entry or path.startswith(entry + "/")


def guard_patterns(
    compose_cfg: DockerConfig | None, host_scripts: tuple[str, ...]
) -> tuple[str, ...]:
    """Protected patterns: the compose config's (or the defaults), the host scripts and
    the compose file. Without a compose config the default patterns still apply."""
    protected = compose_cfg.protected_paths if compose_cfg is not None else DEFAULT_PROTECTED_PATHS
    return tuple(dict.fromkeys((*protected, *host_scripts, "docker-compose.yml")))


def _git_bytes(worktree: Path, args: list[str]) -> bytes:
    proc = subprocess.run(["git", *args], cwd=worktree, check=False, capture_output=True)
    if proc.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {proc.stderr.decode(errors='replace')}")
    return proc.stdout


def _base_content_violations(
    worktree: Path, base_ref: str, patterns: tuple[str, ...], skipped: Callable[[str], bool]
) -> list[str]:
    """Compare protected files of the base commit byte for byte with the worktree.

    Independent of git attributes (eol/encoding filters) and of git's change detection:
    the blob comes from `cat-file blob` (raw) and the worktree is read directly.
    """
    listing = _git_bytes(worktree, ["ls-tree", "-r", "-z", base_ref]).split(b"\0")
    flagged: list[str] = []
    for entry in listing:
        if not entry:
            continue
        meta, _, raw_path = entry.partition(b"\t")
        mode, kind, sha = meta.decode().split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if kind != "blob" or skipped(path) or not any(fnmatch(path, pat) for pat in patterns):
            continue
        blob = _git_bytes(worktree, ["cat-file", "blob", sha])
        target = worktree / path
        try:
            if mode == "120000":
                same = target.is_symlink() and os.readlink(target).encode(
                    "utf-8", errors="surrogateescape"
                ) == blob
            else:
                st = target.lstat()
                same = (
                    stat.S_ISREG(st.st_mode)
                    and bool(st.st_mode & 0o111) == (mode == "100755")
                    and target.read_bytes() == blob
                )
        except OSError:
            same = False
        if not same:
            flagged.append(path)
    return flagged


def guard_violations(
    worktree: Path,
    base_ref: str,
    patterns: tuple[str, ...],
    host_copies: tuple[str, ...] = (),
) -> list[str]:
    """Return sorted paths that may not be run or mounted because they differ from base.

    Two checks, combined:
    - every protected file in the base commit must be byte-identical (type, mode and
      content, read raw) in the worktree, so `.gitattributes` tricks cannot hide edits;
    - any touched or gitignored path matching a pattern is flagged (covers new files).
    Ignored directories are listed collapsed (no trailing slash), so a path is also
    matched with a trailing slash. Paths in or under a host_copies entry are skipped
    because the host overwrites them anyway.
    """

    def skipped(path: str) -> bool:
        return any(_under(path, entry) for entry in host_copies)

    flagged = set(_base_content_violations(worktree, base_ref, patterns, skipped))
    candidates = set(touched_paths(worktree, base_ref)) | set(ignored_paths(worktree))
    for path in candidates:
        if skipped(path):
            continue
        if any(fnmatch(path, pat) or fnmatch(path + "/", pat) for pat in patterns):
            flagged.add(path)
    return sorted(flagged)


def _safe_path(root: Path, rel: str) -> Path:
    """Join root and rel; refuse escapes and any symlink along the way."""
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"Unsafe path in docker config: {rel!r}")
    current = root
    for part in Path(rel).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink in {root}: {current}")
    return current


def _include_filter(patterns: tuple[str, ...]) -> Callable[[str, list[str]], set[str]] | None:
    """copytree `ignore` for a host-copies include filter: keep folders and the files
    matching a pattern; drop everything else, symlinks included. No patterns: copy all."""
    if not patterns:
        return None

    def ignore(directory: str, names: list[str]) -> set[str]:
        dropped: set[str] = set()
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                dropped.add(name)
            elif path.is_dir():
                continue
            elif not any(fnmatch(name, pat) for pat in patterns):
                dropped.add(name)
        return dropped

    return ignore


def prepare_worktree(cfg: DockerConfig, worktree: Path, repo: Path) -> None:
    """Copy host_copies from the main checkout and create create_dirs (after the guard)."""
    includes = dict(cfg.host_copy_includes)
    for entry in cfg.host_copies:
        source = _safe_path(repo, entry)
        target = _safe_path(worktree, entry)
        if not source.is_dir():
            raise ValueError(f"host_copies source is not a directory: {source}")
        try:
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                source, target, symlinks=True, ignore=_include_filter(includes.get(entry, ()))
            )
        except OSError as exc:  # e.g. root-owned 0600 keys in nginx-proxy/certs
            raise ValueError(f"could not copy {entry}: {exc}") from exc
    for entry in cfg.create_dirs:
        _safe_path(worktree, entry).mkdir(parents=True, exist_ok=True)


def compose_env(cfg: DockerConfig, worktree: Path, repo: Path) -> dict[str, str]:
    """Environment for compose; the .env comes from the main checkout, never the worktree."""
    env = dict(os.environ)
    env["COMPOSE_PROJECT_NAME"] = cfg.project_name
    env["COMPOSE_FILE"] = str(worktree / "docker-compose.yml")
    env["COMPOSE_PROFILES"] = cfg.profile
    env_file = repo / ".env"
    if env_file.is_file():
        env["COMPOSE_ENV_FILES"] = str(env_file)
    return env


def up_command(cfg: DockerConfig, worktree: Path, repo: Path) -> list[str]:
    """Build the `docker compose up` argv."""
    env_file = repo / ".env"
    return [
        "docker",
        "compose",
        "--project-name",
        cfg.project_name,
        "--project-directory",
        str(worktree),
        "--file",
        str(worktree / "docker-compose.yml"),
        *(["--env-file", str(env_file)] if env_file.is_file() else []),
        "--profile",
        cfg.profile,
        "up",
        "-d",
        "--wait",
        "--wait-timeout",
        str(cfg.up_timeout),
        *cfg.services,
    ]


def base_script_copy(
    worktree: Path, base_ref: str, script: str, dest_dir: Path, *, executable: bool = False
) -> Path:
    """Write the base commit's blob of `script` (repo-relative) into dest_dir.

    dest_dir must be outside the worktree. The copy keeps the script's file name (so
    `$0` looks the same); `executable` makes it 0700. Raises ValueError if base has no
    such file, or when it is not a regular file there (a symlink's blob is only the link
    target, e.g. `docker/run.sh`: running it would run that unprotected worktree file).
    """
    listing = _git_bytes(worktree, ["ls-tree", "-z", base_ref, "--", script])
    entries = [e for e in listing.split(b"\0") if e]
    if len(entries) != 1:
        raise ValueError(f"{script} is not in the base commit")
    meta, _, raw_path = entries[0].partition(b"\t")
    mode, kind, sha = meta.decode().split()
    if raw_path.decode("utf-8", errors="surrogateescape") != script:
        raise ValueError(f"{script} is not in the base commit")
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ValueError(
            f"{script} is not a regular file in the base commit (mode {mode}, {kind}); "
            "symlinks and folders are refused"
        )
    blob = _git_bytes(worktree, ["cat-file", "blob", sha])
    target = dest_dir / Path(script).name
    target.write_bytes(blob)
    if executable:
        target.chmod(0o700)
    return target


def run_command(
    argv: list[str],
    *,
    cwd: Path | None,
    env: dict[str, str] | None,
    timeout: int,
) -> tuple[str, str]:
    """Run one command; return (status, output)."""
    try:
        proc = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return f"FAIL (timeout after {timeout}s)", ""
    status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
    return status, (proc.stdout + proc.stderr).rstrip()
