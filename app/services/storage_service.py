from supabase import create_client

from app.core.config import settings

_client = create_client(settings.supabase_url, settings.supabase_service_key)
_bucket = _client.storage.from_(settings.supabase_bucket)


def save(key: str, data: bytes, content_type: str) -> None:
    _bucket.upload(key, data, {"content-type": content_type})


def read(key: str) -> bytes:
    return _bucket.download(key)


def delete(keys: list[str]) -> None:
    for i in range(0, len(keys), 100):          # Supabase removes in batches
        _bucket.remove(keys[i:i + 100])


def signed_url(key: str, expires_in: int = 3600) -> str:
    result = _bucket.create_signed_url(key, expires_in)
    return result["signedURL"]

def signed_urls(keys: list[str], expires_in: int = 3600) -> dict[str, str]:
    """Sign many files in ONE request. Returns {storage_key: url}."""
    if not keys:
        return {}
    results = _bucket.create_signed_urls(keys, expires_in)
    return {r["path"]: r.get("signedURL") or r.get("signedUrl") for r in results}



def delete_quietly(keys: list[str]) -> None:
    """Best-effort cleanup: log failures instead of failing the request."""
    if not keys:
        return
    try:
        delete(keys)
    except Exception as e:
        print(f"⚠️ Storage cleanup failed for {len(keys)} file(s): {e}")