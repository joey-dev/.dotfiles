"""Environment variables for the sandbox.

bwrap would normally pass all host variables (including tokens) into the
sandbox. Instead, the sandbox gets:

- a short allowlist of host variables, and
- if a Nix flake is configured: the variables of its dev shell, captured in a
  clean environment (so no host secrets can sneak in that way either).
"""

from __future__ import annotations

import os
import re
import subprocess
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

HOST_ENV_ALLOWLIST: tuple[str, ...] = (
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "SHELL",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOCALE_ARCHIVE",  # nixpkgs programs find their locales here
    "TERM",
    "TERMINFO",
    "TERMINFO_DIRS",  # lets programs know terminals like ghostty
    "COLORTERM",
    "TZ",
    "NIX_SSL_CERT_FILE",
    "SSL_CERT_FILE",
)

# Dev shell variables that point to host-only places or describe the shell itself.
_DEV_SHELL_SKIP: frozenset[str] = frozenset(
    {"TMP", "TMPDIR", "TEMP", "TEMPDIR", "PWD", "OLDPWD", "SHLVL", "_", "HOME"}
)
_VALID_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NIX_PLACEHOLDER_PATH = "/no-such-path"  # nix develop adds this to PATH


@cache
def dev_shell_env(flake: Path) -> dict[str, str]:
    """Return the variables of `nix develop <flake>`, run once per process.

    The environment is written to a file, not stdout, because a shellHook may
    print a banner. --ignore-environment keeps host variables (and secrets) out.
    """
    with TemporaryDirectory(prefix="cw-devshell-") as folder:
        env_file = Path(folder) / "env"
        proc = subprocess.run(
            [
                "nix", "develop", str(flake),
                "--ignore-environment", "--keep", "HOME",
                "--command", "sh", "-c", 'env -0 > "$1"', "sh", str(env_file),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"nix develop {flake} failed: {proc.stderr.strip()}")
        raw = env_file.read_text(encoding="utf-8") if env_file.is_file() else ""

    variables: dict[str, str] = {}
    for entry in raw.split("\0"):
        name, sep, value = entry.partition("=")
        if sep and _VALID_NAME.fullmatch(name) and name not in _DEV_SHELL_SKIP:
            variables[name] = value
    return variables


def _join_paths(*paths: str) -> str:
    """Join PATH strings in order, without duplicates or nix's placeholder."""
    seen: list[str] = []
    for path in paths:
        for entry in path.split(":"):
            if entry and entry != _NIX_PLACEHOLDER_PATH and entry not in seen:
                seen.append(entry)
    return ":".join(seen)


def sandbox_env(flake: Path | None) -> dict[str, str]:
    """Build the full environment for a sandboxed command."""
    env = {name: os.environ[name] for name in HOST_ENV_ALLOWLIST if name in os.environ}
    if flake is not None:
        dev = dict(dev_shell_env(flake))  # copy: the cached dict must stay unchanged
        dev_path = dev.pop("PATH", "")
        env.update(dev)
        # Dev shell tools first, then the host tools (claude, git, socat).
        env["PATH"] = _join_paths(dev_path, os.environ.get("PATH", ""))
    return env
