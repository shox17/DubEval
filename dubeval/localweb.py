"""What DubEval's local servers share: this-machine-only Host check, security headers, and a port bound up front.

The web interface (`dubeval web`), the labelling page (`dubeval label`) and the REST API (`dubeval serve`) use it.
"""
import socket
import sys
from typing import Callable, Optional

LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")

# The web interface loads only its own files: no inline script, nothing from other sites.
PAGE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
            "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'")
# A saved HTML report: its own inline styles and the videos next to it, never a script.
REPORT_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; media-src 'self'; sandbox"


def is_local_host(host_header: Optional[str]) -> bool:
    """Whether a request's Host header names this machine (a DNS-rebinding site's name does not)."""
    return (host_header or "").rsplit(":", 1)[0].lower() in LOCAL_HOSTS


def add_security_headers(app, csp: Optional[Callable[[str], Optional[str]]] = None) -> None:
    """Adds nosniff, no-referrer and no-framing to every response, and csp(path)'s policy when it gives one.

    A route that sets its own Content-Security-Policy keeps it.
    """
    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        policy = csp(request.url.path) if csp else None
        if policy:
            response.headers.setdefault("Content-Security-Policy", policy)
        return response


def bind(host: str = "127.0.0.1", port: int = 0) -> socket.socket:
    """A socket already bound to host:port (a free port when 0), so the link printed next is the one served.

    Picking a free port and binding it later left a gap in which another program could take the port and receive
    the launch link. On Windows the port is also exclusive: no other program can bind it alongside.
    """
    family = socket.AF_INET6 if ":" in host.strip("[]") else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    if sys.platform == "win32":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host.strip("[]"), port))
        sock.listen(2048)                          # listening at once: on Linux a bound-only port can be shared
    except OSError:
        sock.close()
        raise
    return sock


def run(app, sock: socket.socket, log_level: str = "warning") -> None:
    """Serves app on the bound socket until stopped."""
    import uvicorn
    uvicorn.Server(uvicorn.Config(app, log_level=log_level)).run(sockets=[sock])
