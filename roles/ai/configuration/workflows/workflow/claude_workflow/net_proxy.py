"""Host-side HTTP CONNECT allowlist proxy over a Unix domain socket."""

from __future__ import annotations

import contextlib
import os
import socket
import tempfile
import threading
from pathlib import Path
from types import TracebackType

# api.anthropic.com: the Claude API. platform.claude.com: login token refresh.
DEFAULT_ALLOWED_HOSTS: tuple[str, ...] = ("api.anthropic.com", "platform.claude.com")
_BUFFER_SIZE = 65536
_HEADER_LIMIT = 8192


def _relay(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(_BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            dst.shutdown(socket.SHUT_WR)


def _parse_connect_target(header_bytes: bytes) -> tuple[str, str, int] | None:
    try:
        first_line = header_bytes.split(b"\r\n", 1)[0].decode("ascii")
        parts = first_line.split()
        if len(parts) < 2:
            return None
        method, target = parts[0].upper(), parts[1]
        if method != "CONNECT":
            return (method, "", 0)
        if ":" not in target:
            return (method, target.lower(), 443)
        host, port_str = target.rsplit(":", 1)
        return (method, host.lower(), int(port_str))
    except (UnicodeDecodeError, ValueError):
        return None


class ConnectAllowlistProxy:
    """Minimal HTTP CONNECT proxy on a Unix socket enforcing a host:443 allowlist."""

    def __init__(
        self,
        allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
        *,
        allowed_port: int = 443,
        connect_timeout: float = 15.0,
        log_path: Path | None = None,
    ) -> None:
        self._allowed_hosts = frozenset(h.lower() for h in allowed_hosts)
        self._allowed_port = allowed_port
        self._connect_timeout = connect_timeout
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self._server: socket.socket | None = None
        self._stop_event = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._clients: set[socket.socket] = set()
        self._workers: set[threading.Thread] = set()
        self._lock = threading.Lock()
        self._log_path = log_path
        self.socket_path: Path = Path()

    def __enter__(self) -> ConnectAllowlistProxy:
        self._tmpdir = tempfile.TemporaryDirectory(prefix="cw-proxy-")
        self.socket_path = Path(self._tmpdir.name) / "proxy.sock"
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(self.socket_path))
        srv.listen(32)
        srv.settimeout(0.5)
        self._server = srv
        self._stop_event.clear()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop_event.set()
        if self._server is not None:
            with contextlib.suppress(OSError):
                self._server.close()
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2.0)
        with self._lock:
            clients = tuple(self._clients)
            workers = tuple(self._workers)
        for client in clients:
            with contextlib.suppress(OSError):
                client.shutdown(socket.SHUT_RDWR)
        for worker in workers:
            worker.join(timeout=1.0)
        if self._tmpdir is not None:
            self._tmpdir.cleanup()

    def _log(self, line: str) -> None:
        """Append one decision to the log file, if there is one."""
        if self._log_path is None:
            return
        # O_NOFOLLOW: the log lives where the sandbox can write, so it may be a planted
        # symlink. Then opening fails and the line is skipped.
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW
        with self._lock, contextlib.suppress(OSError):
            fd = os.open(self._log_path, flags, 0o600)
            with os.fdopen(fd, "a") as log:
                log.write(line + "\n")

    def _accept_loop(self) -> None:
        assert self._server is not None
        while not self._stop_event.is_set():
            try:
                conn, _ = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
            with self._lock:
                self._clients.add(conn)
                self._workers.add(t)
            t.start()

    def _handle_client(self, conn: socket.socket) -> None:
        upstream: socket.socket | None = None
        try:
            conn.settimeout(self._connect_timeout)
            buf = b""
            while b"\r\n\r\n" not in buf and len(buf) < _HEADER_LIMIT:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf += chunk

            header, delimiter, payload = buf.partition(b"\r\n\r\n")
            parsed = (
                _parse_connect_target(header)
                if delimiter and len(header) + len(delimiter) <= _HEADER_LIMIT
                else None
            )
            if parsed is None:
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return

            method, host, port = parsed
            if method != "CONNECT":
                self._log(f"REJECT {method}")
                conn.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                return

            if host not in self._allowed_hosts or port != self._allowed_port:
                self._log(f"DENY {host}:{port}")
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                return

            self._log(f"ALLOW {host}:{port}")

            upstream = socket.create_connection((host, port), timeout=self._connect_timeout)
            with self._lock:
                self._clients.add(upstream)
                if self._stop_event.is_set():
                    return
            if payload:
                upstream.sendall(payload)
            upstream.settimeout(None)
            conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            conn.settimeout(None)

            t1 = threading.Thread(target=_relay, args=(conn, upstream), daemon=True)
            t2 = threading.Thread(target=_relay, args=(upstream, conn), daemon=True)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
        except OSError:
            with contextlib.suppress(OSError):
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        finally:
            with self._lock:
                self._clients.discard(conn)
                if upstream is not None:
                    self._clients.discard(upstream)
                self._workers.discard(threading.current_thread())
            with contextlib.suppress(OSError):
                conn.close()
            if upstream is not None:
                with contextlib.suppress(OSError):
                    upstream.close()
