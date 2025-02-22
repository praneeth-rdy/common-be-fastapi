import asyncio
from functools import wraps


def async_cache(async_fn):
    """
    Async cache decorator

    Caches the result of an async function in memory for the same arguments.
    Use it for async functions where arguments don't change very often, for example fetching constants from database
    """
    lock = asyncio.Lock()
    cache = {}

    @wraps(async_fn)
    async def inner(*args, **kwargs):
        cache_key = (args, tuple(kwargs.items()))
        if cache_key in cache:
            return cache[cache_key]

        async with lock:
            if cache_key not in cache:
                cache[cache_key] = await async_fn(*args, **kwargs)
        return cache[cache_key]

    return inner
