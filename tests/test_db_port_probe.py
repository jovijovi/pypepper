"""Unit tests for devenv TCP probes used to skip DB integration tests."""

from __future__ import annotations

import socket


def test_tcp_port_open_false_for_closed_port(tcp_port_open_fn):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    port = int(srv.getsockname()[1])
    srv.close()
    assert tcp_port_open_fn("127.0.0.1", port) is False


def test_tcp_port_open_true_for_listening_port(tcp_port_open_fn):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = int(srv.getsockname()[1])
    try:
        assert tcp_port_open_fn("127.0.0.1", port) is True
    finally:
        srv.close()
