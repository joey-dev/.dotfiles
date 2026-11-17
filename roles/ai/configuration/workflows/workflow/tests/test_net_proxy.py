"""Tests for claude_workflow.net_proxy."""

from __future__ import annotations

import socket
import threading

from claude_workflow.net_proxy import ConnectAllowlistProxy


def test_proxy_rejects_non_connect_and_disallowed_hosts() -> None:
    with ConnectAllowlistProxy(allowed_hosts=("api.anthropic.com",)) as proxy:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(proxy.socket_path))
            sock.sendall(b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n")
            resp = sock.recv(1024)
            assert resp.startswith(b"HTTP/1.1 405")

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(proxy.socket_path))
            sock.sendall(b"CONNECT evil.example.com:443 HTTP/1.1\r\n\r\n")
            resp = sock.recv(1024)
            assert resp.startswith(b"HTTP/1.1 403")

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(str(proxy.socket_path))
            sock.sendall(b"CONNECT api.anthropic.com:80 HTTP/1.1\r\n\r\n")
            resp = sock.recv(1024)
            assert resp.startswith(b"HTTP/1.1 403")


def test_proxy_tunnels_allowed_host_and_port() -> None:
    echo_srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    echo_srv.bind(("127.0.0.1", 0))
    echo_srv.listen(1)
    echo_port = echo_srv.getsockname()[1]

    def serve_once() -> None:
        conn, _ = echo_srv.accept()
        with conn:
            data = conn.recv(1024)
            conn.sendall(b"echo:" + data)

    t = threading.Thread(target=serve_once, daemon=True)
    t.start()

    try:
        with ConnectAllowlistProxy(
            allowed_hosts=("127.0.0.1",),
            allowed_port=echo_port,
        ) as proxy:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(proxy.socket_path))
                sock.sendall(f"CONNECT 127.0.0.1:{echo_port} HTTP/1.1\r\n\r\n".encode("ascii"))
                headers = sock.recv(1024)
                assert headers.startswith(b"HTTP/1.1 200")
                sock.sendall(b"ping")
                sock.shutdown(socket.SHUT_WR)
                body = sock.recv(1024)
                assert body == b"echo:ping"
    finally:
        echo_srv.close()
        t.join(timeout=2.0)
