"""Host-side Docker test stack: guard, worktree preparation and command builders.

Claude never gets Docker access. The host starts the compose stack from the ticket's
worktree and runs host commands, but only after `guard_violations` confirms that no
Docker-related file differs from the base commit, and `symlink_violations` confirms
that the worktree has no new symlinks (Docker follows symlinked mount sources).
Docker runs only in the rootless `cw-docker` daemon (see `require_rootless`).
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, cast

from claude_workflow.config import DEFAULT_PROTECTED_PATHS, DockerConfig
from claude_workflow.git_host import ignored_paths, touched_paths

# Extra seconds for `up` to build images before `--wait-timeout` starts counting.
UP_BUILD_HEADROOM = 600

# Sockets of the root Docker daemon. The workflow must never talk to these.
ROOT_DOCKER_SOCKETS = (Path("/var/run/docker.sock"), Path("/run/docker.sock"))


def socket_path(docker_host: str) -> str:
    """The socket file of a `unix://` docker host."""
    return docker_host.removeprefix("unix://")


def require_rootless(docker_host: str | None, worktree_base: Path) -> str:
    """Return docker_host if it is safe to use; raise ValueError (for the human) if not.

    Refused: no host configured (an inherited DOCKER_HOST does not count), a host that is
    not a `unix://` URI with an absolute path, a socket that resolves (symlinks
    included) to a root Docker socket, and a worktree base inside $HOME (the rootless
    daemon runs as another user and cannot read it).
    """
    if not docker_host:
        raise ValueError(
            "no docker-host is configured. Set docker-host to the rootless Docker socket "
            "(unix:///var/lib/cw-docker-sock/docker.sock); the workflow never uses root Docker."
        )
    if not docker_host.startswith("unix:///"):
        raise ValueError(
            f"docker-host must be a unix:// URI with an absolute path, got {docker_host!r}"
        )
    socket = Path(socket_path(docker_host))
    if socket.resolve() in {root.resolve() for root in ROOT_DOCKER_SOCKETS}:
        raise ValueError(
            f"docker-host {docker_host!r} points at root Docker; use the rootless "
            "cw-docker socket instead."
        )
    home = Path.home().resolve()
    base = worktree_base.resolve()
    if base == home or home in base.parents:
        raise ValueError(
            f"worktree-base {worktree_base} is inside your home folder, which cw-docker "
            "can't read. Set worktree-base to a folder outside $HOME that cw-docker can read."
        )
    return docker_host


def docker_env(docker_host: str) -> dict[str, str]:
    """Copy of the environment with DOCKER_HOST set (overrides an inherited one)."""
    env = dict(os.environ)
    env["DOCKER_HOST"] = docker_host
    env.pop("DOCKER_CONTEXT", None)  # a shell context must not override DOCKER_HOST
    return env


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
                    # Owner execute bit only, like git (the worktree ACL adds "other" x).
                    and bool(st.st_mode & stat.S_IXUSR) == (mode == "100755")
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


def _base_symlinks(worktree: Path, base_ref: str) -> dict[str, bytes]:
    """Symlinks in the base commit: path -> link target (raw blob bytes)."""
    listing = _git_bytes(worktree, ["ls-tree", "-r", "-z", base_ref]).split(b"\0")
    links: dict[str, bytes] = {}
    for entry in listing:
        if not entry:
            continue
        meta, _, raw_path = entry.partition(b"\t")
        mode, kind, sha = meta.decode().split()
        if mode == "120000" and kind == "blob":
            path = raw_path.decode("utf-8", errors="surrogateescape")
            links[path] = _git_bytes(worktree, ["cat-file", "blob", sha])
    return links


def _is_symlink_or_unsure(path: Path) -> bool:
    """lstat says symlink, or lstat fails for any reason but "not there" (fail closed)."""
    try:
        return stat.S_ISLNK(path.lstat().st_mode)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return True


def symlink_violations(
    worktree: Path, base_ref: str, host_copies: tuple[str, ...] = ()
) -> list[str]:
    """Return sorted worktree paths that are symlinks the base commit does not have.

    Docker follows a symlinked bind-mount source (`./api-documentation` ->
    `$HOME`), so no new symlink may sit on any touched or gitignored path, nor on any
    parent folder of one. A symlink that the base commit has at the same path with the
    same target is allowed. Paths strictly inside a host_copies entry are skipped (the
    host replaces them before `up`); the entry itself is still checked. Any doubt
    (an odd path, an lstat error) counts as a violation.
    """
    candidates = set(touched_paths(worktree, base_ref)) | set(ignored_paths(worktree))
    to_check: set[str] = set()
    flagged: set[str] = set()
    for path in candidates:
        parts = Path(path).parts
        if not parts or Path(path).is_absolute() or ".." in parts:
            flagged.add(path)
            continue
        for depth in range(1, len(parts) + 1):
            to_check.add("/".join(parts[:depth]))
    to_check = {
        p for p in to_check if not any(p != entry and _under(p, entry) for entry in host_copies)
    }
    links = [p for p in to_check if _is_symlink_or_unsure(worktree / p)]
    if links:
        base_links = _base_symlinks(worktree, base_ref)
        for rel in links:
            try:
                target = os.readlink(worktree / rel).encode("utf-8", errors="surrogateescape")
            except OSError:
                flagged.add(rel)
                continue
            if base_links.get(rel) != target:
                flagged.add(rel)
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


def _make_group_writable(root: Path) -> None:
    """Give the group read-write (folders also x) on a copied tree.

    copytree keeps the source modes (0755/0644). With the worktree ACL, the group bits are
    the ACL mask, so they would cap `cw-docker` (container root) at read-only and services
    like proxy-companion could not write into the copy. Symlinks are left alone.
    """
    for path in (root, *root.rglob("*")):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        extra = 0o070 if path.is_dir() else 0o060
        path.chmod(stat.S_IMODE(mode) | extra)


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
            _make_group_writable(target)
        except OSError as exc:  # e.g. root-owned 0600 keys in nginx-proxy/certs
            raise ValueError(f"could not copy {entry}: {exc}") from exc
    for entry in cfg.create_dirs:
        _safe_path(worktree, entry).mkdir(parents=True, exist_ok=True)


def compose_env(
    cfg: DockerConfig,
    worktree: Path,
    repo: Path,
    docker_host: str,
    override: Path | None = None,
) -> dict[str, str]:
    """Environment for compose; the .env comes from the main checkout, never the worktree.

    With `override`, it is appended to COMPOSE_FILE after the worktree's compose file.
    """
    env = docker_env(docker_host)
    env["COMPOSE_PROJECT_NAME"] = cfg.project_name
    compose_file = str(worktree / "docker-compose.yml")
    env["COMPOSE_FILE"] = f"{compose_file}:{override}" if override is not None else compose_file
    env["COMPOSE_PROFILES"] = cfg.profile
    env_file = repo / ".env"
    if env_file.is_file():
        env["COMPOSE_ENV_FILES"] = str(env_file)
    return env


def _compose_argv(
    cfg: DockerConfig, worktree: Path, repo: Path, override: Path | None
) -> list[str]:
    """The `docker compose` prefix shared by `config` and `up`."""
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
        *(["--file", str(override)] if override is not None else []),
        *(["--env-file", str(env_file)] if env_file.is_file() else []),
        "--profile",
        cfg.profile,
    ]


def down_command(
    cfg: DockerConfig, worktree: Path, repo: Path, override: Path | None = None
) -> list[str]:
    """`docker compose down` for the project; keeps volumes (database data)."""
    return [*_compose_argv(cfg, worktree, repo, override), "down", "--remove-orphans"]


def up_command(
    cfg: DockerConfig, worktree: Path, repo: Path, override: Path | None = None
) -> list[str]:
    """Build the `docker compose up` argv (with `override` as a second compose file)."""
    return [
        *_compose_argv(cfg, worktree, repo, override),
        "up",
        "-d",
        "--wait",
        "--wait-timeout",
        str(cfg.up_timeout),
        *cfg.services,
    ]


# Sources of the root Docker socket in the compose file's bind mounts.
_ROOT_SOCKET_SOURCES = frozenset(str(path) for path in ROOT_DOCKER_SOCKETS)


def socket_override(model: dict[str, Any], socket: str) -> dict[str, Any]:
    """Compose override that repoints the root `docker.sock` bind mounts at `socket`.

    `model` is the output of `docker compose config --format json`. Only the socket
    mounts are listed per service (compose merges `volumes` by target); services
    without one are left out, so a model without socket mounts gives no services.
    """
    services: dict[str, Any] = {}
    model_services = cast("dict[str, dict[str, Any]]", model.get("services") or {})
    for name, service in model_services.items():
        listed = cast("list[Any]", service.get("volumes") or [])
        volumes: list[dict[str, Any]] = []
        for entry in listed:
            if isinstance(entry, dict):
                volume = cast("dict[str, Any]", entry)
                if volume.get("source") in _ROOT_SOCKET_SOURCES:
                    volumes.append({**volume, "source": socket})
        if volumes:
            services[name] = {"volumes": volumes}
    return {"services": services}


def compose_model(
    cfg: DockerConfig, worktree: Path, repo: Path, docker_host: str
) -> dict[str, Any]:
    """The resolved compose model (`docker compose config --format json`), read through
    the rootless daemon's environment. Raises ValueError on a failed command or bad JSON."""
    argv = [*_compose_argv(cfg, worktree, repo, None), "config", "--format", "json"]
    status, output = run_command(
        argv,
        cwd=worktree,
        env=compose_env(cfg, worktree, repo, docker_host),
        timeout=cfg.up_timeout,
    )
    if status != "PASS":
        raise ValueError(f"docker compose config failed: {status}: {output}")
    # stdout and stderr are merged: skip warnings before the JSON object.
    start = output.find("{")
    try:
        model, _ = json.JSONDecoder().raw_decode(output[start:]) if start >= 0 else (None, 0)
    except json.JSONDecodeError as exc:
        raise ValueError(f"docker compose config gave invalid JSON: {exc}") from exc
    if not isinstance(model, dict):
        raise ValueError("docker compose config gave no JSON object")
    return cast("dict[str, Any]", model)


def override_path(state_base: Path, cfg: DockerConfig) -> Path:
    """Where the generated override lives: outside the worktree and every sandbox bind."""
    return state_base / "compose" / f"{cfg.project_name}.override.json"


def write_override(path: Path, override: dict[str, Any]) -> None:
    """Write the override as JSON (valid YAML, so compose reads it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(override, indent=2) + "\n")


def port_hint(output: str) -> str:
    """Add a hint line to a failed `up` output when a port is taken."""
    if "address already in use" in output or "port is already allocated" in output:
        return (
            output + "\nHint: a host port is taken (a dev stack on :80/:443?). "
            "Please stop your dev stack and try again."
        )
    return output


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
    """Run one command; return (status, output). Never raises for a command that
    cannot start: that is a FAIL too, so Verify keeps going."""
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
    except OSError as exc:  # missing program or cwd, ENOEXEC, permission denied, ...
        return f"FAIL (could not start: {exc})", ""
    status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
    return status, (proc.stdout + proc.stderr).rstrip()
