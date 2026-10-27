"""The computer's network settings: its certificates and proxy, and plain messages when a network blocks DubEval."""
import os
import sys
import types

import pytest
import requests

from dubeval import inputs, network, perso_api


def test_a_blocked_secure_connection_says_so():
    ssl_error = requests.exceptions.SSLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                                             "self-signed certificate in certificate chain")
    assert network.describe(ssl_error, "default") == network.CERT_BLOCKED
    wrapped = RuntimeError("download failed")
    wrapped.__cause__ = ssl_error                                    # found through the chain of causes
    assert network.describe(wrapped, "default") == network.CERT_BLOCKED


def test_a_refusing_proxy_says_so_and_anything_else_keeps_the_default():
    assert network.describe(requests.exceptions.ProxyError("407 Proxy Authentication Required"), "d") == \
        network.PROXY_FAILED
    assert network.describe(requests.exceptions.ConnectionError("Name or service not known"), "d") == "d"


def test_the_proxy_comes_from_a_windows_proxy_list():
    assert network.first_proxy("proxy.corp:8080") == "proxy.corp:8080"
    assert network.first_proxy("http=h:80;https=s:443") == "s:443"
    assert network.first_proxy("a:1 b:2") == "a:1"
    assert network.first_proxy("") is None and network.first_proxy(None) is None


def test_a_found_proxy_is_used_but_never_for_this_computer(monkeypatch):
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HTTP_PROXY", "http://chosen-by-you:3128")       # one already set wins
    network.apply_proxy("proxy.corp:8080")
    assert os.environ["HTTPS_PROXY"] == "http://proxy.corp:8080" and os.environ["HTTP_PROXY"] == "http://chosen-by-you:3128"
    assert "127.0.0.1" in os.environ["NO_PROXY"] and "localhost" in os.environ["NO_PROXY"]


def test_start_up_trusts_the_systems_certificates_unless_turned_off(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "truststore", types.SimpleNamespace(inject_into_ssl=lambda: calls.append(1)))
    monkeypatch.setattr(network, "_done", False)
    monkeypatch.setattr(network.os, "name", "posix")                  # no proxy lookup in this test
    network.use_system_settings()                                     # conftest turns it off for the test run
    assert calls == []
    monkeypatch.setenv("DUBEVAL_SYSTEM_NETWORK", "1")
    network.use_system_settings()
    network.use_system_settings()                                     # once per process
    assert calls == [1]


class Refused:
    """A session whose every request is refused by a network that re-signs secure connections."""
    def request(self, *a, **k):
        raise requests.exceptions.SSLError("certificate verify failed: self-signed certificate in certificate chain")
    get = request


def test_a_perso_link_on_a_blocking_network_explains_the_cause():
    with pytest.raises(perso_api.PersoError, match="blocked DubEval's secure connection"):
        perso_api._public_get(Refused(), "https://api.perso.ai/x", sleep=lambda s: None)


def test_a_link_download_on_a_blocking_network_explains_the_cause(tmp_path):
    with pytest.raises(ValueError, match="blocked DubEval's secure connection"):
        inputs.fetch("https://example.com/a.mp4", tmp_path, "dub", session=Refused(), sleep=lambda s: None)
