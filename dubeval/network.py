"""The computer's own network settings for DubEval's downloads: its trusted certificates and its proxy.

Company networks often check secure traffic with security software (Zscaler, Netskope, ...) that re-signs every site
with the company's own certificate. Windows trusts that certificate, so browsers work, but Python trusts only its own
list and refuses the connection. `truststore` makes Python ask the operating system instead, as browsers do.

A proxy set by an automatic configuration script (PAC) or by automatic detection (WPAD) is invisible to Python, which
only reads a fixed proxy. On Windows, WinHTTP (the system's own HTTP stack) evaluates the script; the proxy it names is
set as HTTP(S)_PROXY, which requests, httpx and yt-dlp all follow, with this computer itself excluded (NO_PROXY).

`use_system_settings()` runs once at start-up (cli.main). DUBEVAL_SYSTEM_NETWORK=0 turns it off.
"""
import logging
import os
import threading
from typing import Optional

log = logging.getLogger(__name__)

PROBE_URL = "https://huggingface.co/"         # where the proxy is looked up for (the models' host)
LOCAL = "localhost,127.0.0.1,::1"             # DubEval's own page and the local judge never go through a proxy
PROXY_TIMEOUT_MS = 5000                       # automatic detection on a network without it must not hang start-up

CERT_BLOCKED = ("This network blocked DubEval's secure connection: a company network or security software checks it "
                "with a certificate this computer doesn't trust. Ask your IT team to allow DubEval, or try another "
                "network.")
PROXY_FAILED = ("This network's proxy didn't let DubEval through. Ask your IT team to allow DubEval, or try another "
                "network.")

_done = False


def use_system_settings() -> None:
    """Trusts the operating system's certificates and, on Windows, finds the system proxy in the background."""
    global _done
    if _done or os.getenv("DUBEVAL_SYSTEM_NETWORK", "1") == "0":
        return
    _done = True
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception as e:                       # never stop DubEval from starting
        log.warning("Couldn't use the system's certificates: %s", e)
    if os.name == "nt" and not (os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")):
        threading.Thread(target=_apply_windows_proxy, name="system-proxy", daemon=True).start()


def _apply_windows_proxy() -> None:
    try:
        proxy = windows_proxy(PROBE_URL)
    except Exception as e:
        log.warning("Couldn't read the system proxy: %s", e)
        return
    if proxy:
        apply_proxy(proxy)


def apply_proxy(proxy: str) -> None:
    """Sends DubEval's web requests through proxy ("host:port"), except to this computer; a proxy already set wins."""
    url = proxy if "://" in proxy else f"http://{proxy}"
    for name in ("HTTPS_PROXY", "HTTP_PROXY"):
        os.environ.setdefault(name, url)
    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    os.environ["NO_PROXY"] = ",".join(x for x in [current, LOCAL] if x)
    log.info("Using the system proxy %s", url)


def first_proxy(listing: Optional[str], scheme: str = "https") -> Optional[str]:
    """The proxy for scheme from a WinHTTP list ("host:port", "https=h:p;http=h:p" or several, ';' or ' ' apart)."""
    entries = [e for e in (listing or "").replace(" ", ";").split(";") if e]
    for entry in entries:                                   # "scheme=host:port" for this scheme first
        if "=" in entry and entry.split("=", 1)[0].lower() == scheme:
            return entry.split("=", 1)[1]
    plain = [e for e in entries if "=" not in e]
    return plain[0] if plain else None


def windows_proxy(url: str) -> Optional[str]:
    """The proxy Windows uses for url ("host:port"), following an automatic configuration script or detection;
    None for a direct connection."""
    import ctypes
    from ctypes import wintypes

    # Strings Windows allocates are kept as raw pointers: they are read with wstring_at and freed with GlobalFree.
    class IEConfig(ctypes.Structure):
        _fields_ = [("fAutoDetect", wintypes.BOOL), ("lpszAutoConfigUrl", ctypes.c_void_p),
                    ("lpszProxy", ctypes.c_void_p), ("lpszProxyBypass", ctypes.c_void_p)]

    class AutoProxyOptions(ctypes.Structure):
        _fields_ = [("dwFlags", wintypes.DWORD), ("dwAutoDetectFlags", wintypes.DWORD),
                    ("lpszAutoConfigUrl", wintypes.LPCWSTR), ("lpvReserved", ctypes.c_void_p),
                    ("dwReserved", wintypes.DWORD), ("fAutoLogonIfChallenged", wintypes.BOOL)]

    class ProxyInfo(ctypes.Structure):
        _fields_ = [("dwAccessType", wintypes.DWORD), ("lpszProxy", ctypes.c_void_p),
                    ("lpszProxyBypass", ctypes.c_void_p)]

    winhttp = ctypes.WinDLL("winhttp", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    winhttp.WinHttpOpen.restype = ctypes.c_void_p
    winhttp.WinHttpOpen.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                    wintypes.DWORD]
    winhttp.WinHttpSetTimeouts.argtypes = [ctypes.c_void_p] + [ctypes.c_int] * 4
    winhttp.WinHttpGetProxyForUrl.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(AutoProxyOptions),
                                              ctypes.POINTER(ProxyInfo)]
    winhttp.WinHttpCloseHandle.argtypes = [ctypes.c_void_p]
    winhttp.WinHttpGetIEProxyConfigForCurrentUser.argtypes = [ctypes.POINTER(IEConfig)]

    def text(pointer) -> Optional[str]:
        return ctypes.wstring_at(pointer) if pointer else None

    def free(*pointers):
        for pointer in pointers:
            if pointer:
                kernel32.GlobalFree(pointer)

    ie = IEConfig()
    if not winhttp.WinHttpGetIEProxyConfigForCurrentUser(ctypes.byref(ie)):
        return None
    try:
        script = text(ie.lpszAutoConfigUrl)
        fixed = first_proxy(text(ie.lpszProxy))
        if not (ie.fAutoDetect or script):
            return fixed                                      # a fixed proxy (Python reads it too) or none
        options = AutoProxyOptions()
        if script:
            options.dwFlags, options.lpszAutoConfigUrl = 2, script        # WINHTTP_AUTOPROXY_CONFIG_URL
        else:
            options.dwFlags, options.dwAutoDetectFlags = 1, 1 | 2         # AUTO_DETECT: DHCP and DNS
        options.fAutoLogonIfChallenged = True
        session = winhttp.WinHttpOpen("DubEval", 1, None, None, 0)        # WINHTTP_ACCESS_TYPE_NO_PROXY
        if not session:
            return fixed
        try:
            winhttp.WinHttpSetTimeouts(session, PROXY_TIMEOUT_MS, PROXY_TIMEOUT_MS, PROXY_TIMEOUT_MS,
                                       PROXY_TIMEOUT_MS)
            info = ProxyInfo()
            if not winhttp.WinHttpGetProxyForUrl(session, url, ctypes.byref(options), ctypes.byref(info)):
                return fixed                                  # no script found: as configured otherwise
            try:
                return first_proxy(text(info.lpszProxy)) if info.dwAccessType == 3 else None   # NAMED_PROXY
            finally:
                free(info.lpszProxy, info.lpszProxyBypass)
        finally:
            winhttp.WinHttpCloseHandle(session)
    finally:
        free(ie.lpszAutoConfigUrl, ie.lpszProxy, ie.lpszProxyBypass)


def describe(error: BaseException, default: str) -> str:
    """The message for a failed connection: a blocked secure connection or proxy when that's the cause, else default."""
    seen, e = set(), error
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        name, text = type(e).__name__, str(e)
        if name == "SSLError" or "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
            return CERT_BLOCKED
        if name == "ProxyError" or "407 Proxy Authentication" in text:
            return PROXY_FAILED
        e = e.__cause__ or e.__context__
    return default
