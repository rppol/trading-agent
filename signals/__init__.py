"""Shared helpers.

macOS system Pythons and uv-managed standalone builds ship without a CA bundle
wired into OpenSSL, so every urlopen against a TLS host raises
CERTIFICATE_VERIFY_FAILED. Three modules had already patched around this
locally; the ingestion path -- the one the whole prototype runs on -- had not.
The result on a clean macOS checkout was `make ingest` printing
{"seen": 0, "new": 0} and exiting 0: a total network failure wearing the
costume of a quiet news day.

certifi is already a declared dependency. This is the single place that uses it.
"""
import ssl


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:               # system store is wired in; use it
        return ssl.create_default_context()
