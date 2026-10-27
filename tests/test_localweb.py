"""What every local server shares: the Host check and the port bound before the link is printed."""
import pytest

from dubeval import localweb


@pytest.mark.parametrize("host, local", [
    ("127.0.0.1:8501", True), ("localhost:8501", True), ("LOCALHOST", True), ("[::1]:8000", True),
    ("evil.example:8501", False), ("127.0.0.1.evil.example", False), ("", False), (None, False),
])
def test_only_this_machines_names_count_as_local(host, local):
    assert localweb.is_local_host(host) is local


def test_a_free_port_is_bound_at_once():
    sock = localweb.bind("127.0.0.1", 0)
    try:
        port = sock.getsockname()[1]
        assert port > 0
        with pytest.raises(OSError):
            localweb.bind("127.0.0.1", port).close()
    finally:
        sock.close()
