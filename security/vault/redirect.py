from urllib.parse import urlsplit


def safe_redirect(target: str, default: str = "/") -> str:
    """Where to send the user after login: only a path on this site (starting with a single '/').
    Anything else, including other hosts and protocol-relative '//host' URLs, goes to `default`."""
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return default
    return target
