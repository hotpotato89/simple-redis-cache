from functools import wraps
import inspect
import json
from logging import Logger, getLogger
from time import time
from typing import Callable, TypeVar, ParamSpec, cast

from redis import Redis

from simple_redis_cache.encoder import CustomJSONEncoder
from simple_redis_cache.key_generator import gen_cache_key


T = TypeVar("T")
P = ParamSpec("P")


class Cache:
    __slots__ = ("redis_client", "logger")

    def __init__(
        self, redis_client: Redis, logger: Logger = getLogger(__name__)
    ) -> None:
        self.redis_client = redis_client
        self.logger = logger

    def cache(
        self, ttl: int, prefix: str | None = None
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        def wrapper(func: Callable[P, T]) -> Callable[P, T]:
            if inspect.iscoroutinefunction(func):
                raise TypeError(
                    f"@cache can only be used on sync functions. "
                    f"'{func.__name__}' is async."
                )

            @wraps(func)
            def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                cache_key = gen_cache_key(func, args, kwargs, prefix)

                try:
                    cached = self.redis_client.get(cache_key)
                    if cached:
                        self.logger.debug("Cache HIT: %s", cache_key)
                        if cached == "__NULL__":
                            return None  # type: ignore # pragma: no cover
                        return json.loads(cached)
                except Exception as exc:
                    self.logger.warning(
                        "Failed cache get for key: %s",
                        cache_key,
                        exc_info=exc,
                    )

                result = func(*args, **kwargs)

                try:
                    if result is None:
                        data_to_cache = "__NULL__"
                    else:
                        data_to_cache = json.dumps(result, cls=CustomJSONEncoder)
                    self.redis_client.set(cache_key, data_to_cache, ex=ttl)
                    self.logger.debug("Cache saved: %s", cache_key)
                except Exception as exc:  # pragma: no cover
                    self.logger.warning(
                        "Failed cache set for key: %s",
                        cache_key,
                        exc_info=exc,
                    )

                return result

            return cast(Callable[P, T], inner)

        return wrapper

    def invalidate_cache(self, prefix: str = "*", timeout_seconds: int = 30) -> int:
        if prefix == "*":
            pattern = "cache:*"
        else:
            pattern = f"cache:{prefix}:*"

        self.logger.debug("Starting cache invalidation by pattern: %s", pattern)

        deleted_count = 0
        cursor = 0
        start_time = time()

        try:
            while True:
                if time() - start_time > timeout_seconds:  # pragma: no cover
                    self.logger.warning(
                        "Cache invalidation timed out (%s)", timeout_seconds
                    )
                    break

                cursor, keys = self.redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100,
                )

                if keys:
                    self.redis_client.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            self.logger.info("Cache invalidated (%s keys)", deleted_count)
            return deleted_count

        except Exception as exc:  # pragma: no cover
            self.logger.error(
                "Failed to invalidate cache",
                exc_info=exc,
            )
            return deleted_count
