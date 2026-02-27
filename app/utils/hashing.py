import hashlib


def sha256_bytes(payload: bytes) -> str:
    """Return a stable SHA256 hex digest for deduplication."""
    return hashlib.sha256(payload).hexdigest()
