from fastapi import Request
from fastapi_cache import FastAPICache
import datetime
import logging

def custom_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response=None,
    *args,
    **kwargs
):
    prefix = FastAPICache.get_prefix()
    query_params = request.query_params if request else {}
    user_id = str(query_params.get("user_id", ""))
    last_created_at = query_params.get("last_created_at", "none")
    limit = str(query_params.get("limit", "10"))

    if last_created_at != "none":
        try:
            last_created_at = datetime.datetime.fromisoformat(last_created_at).isoformat()
        except ValueError:
            last_created_at = "invalid"

    cache_key = f"{prefix}:{namespace}:{func.__module__}:{func.__name__}:{user_id}:{last_created_at}:{limit}"
    logging.getLogger("app").info(f"Сформирован ключ кэша: {cache_key}")
    return cache_key