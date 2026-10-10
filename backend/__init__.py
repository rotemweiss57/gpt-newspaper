import os
import ssl


def _ensure_ca_bundle() -> None:
    """Fall back to certifi's CA bundle when Python has none (e.g. python.org builds on macOS).

    Must run before aiohttp (used by Tavily) is imported, since it caches its SSL context.
    """
    paths = ssl.get_default_verify_paths()
    if paths.cafile or paths.capath or os.getenv("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:
        return
    os.environ["SSL_CERT_FILE"] = certifi.where()


_ensure_ca_bundle()
