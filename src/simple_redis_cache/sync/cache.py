import time
from functools import wraps
import inspect
import json
from logging import Logger, getLogger
from typing import Callable, TypeVar, ParamSpec, cast
import pickle

from redis import Redis

from simple_redis_cache.encoder import CustomJSONEncoder
from simple_redis_cache.key_generator import gen_cache_key


T = TypeVar("T")
P = ParamSpec("P")


class Cache:
    """
    Класс для кэширования результатов синхронных функций в Redis.

    Args:
        redis_client: Клиент Redis из `redis`.
        logger: Опциональный логгер. Если не передан, создаётся автоматически.

    Example:
        >>> from redis import Redis
        >>> from simple_redis_cache.sync import Cache
        >>>
        >>> redis = Redis()
        >>> cache = Cache(redis)
        >>>
        >>> @cache.cache(ttl=60, prefix="user")
        >>> def get_user(user_id: int) -> dict:
        ...     return {"id": user_id, "name": "Alice"}
    """

    __slots__ = ("redis_client", "logger")

    def __init__(
        self, redis_client: Redis, logger: Logger = getLogger(__name__)
    ) -> None:
        self.redis_client = redis_client
        self.logger = logger

    def cache(
        self, ttl: int, prefix: str | None = None, use_pickle: bool = False
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Декоратор для кэширования синхронной функции.

        Args:
            ttl: Время жизни кэша в секундах.
            prefix: Опциональный префикс для ключа кэша.
            use_pickle: Использование pickle в качестве сериализатора

        Returns:
            Декоратор, оборачивающий функцию с кэшированием.

        Raises:
            TypeError: Если функция асинхронная, а не синхронная.

        Example:
            >>> @cache.cache(ttl=60, prefix="user", use_pickle=True)
            >>> def get_user(user_id: int) -> dict:
            ...     return {"id": user_id, "name": "Alice"}
        """

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
                    if cached is not None:
                        self.logger.debug("Cache HIT: %s", cache_key)

                        # Приводим к bytes если это str
                        if isinstance(cached, str): # pragma: no cover
                            cached = cached.encode("utf-8")

                        if cached == b"__NULL__":
                            return None  # type: ignore
                        if cached.startswith(b"PICKLE:"):  # type: ignore
                            return pickle.loads(cached[7:])  # type: ignore
                        return json.loads(cached.decode("utf-8"))  # type: ignore
                except Exception as exc:
                    self.logger.warning(
                        "Failed cache get for key: %s",
                        cache_key,
                        exc_info=exc,
                    )

                result = func(*args, **kwargs)

                try:
                    if result is None:
                        data_to_cache = b"__NULL__"
                    else:
                        if use_pickle:
                            data_to_cache = b"PICKLE:" + pickle.dumps(result)
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
        """
        Удаляет все ключи кэша по префиксу.

        Args:
            prefix: Префикс для удаления. Если `"*"` — удаляет все ключи.
            timeout_seconds: Максимальное время выполнения операции (сек).

        Returns:
            Количество удалённых ключей.

        Example:
            >>> cache.invalidate_cache(prefix="user")
            42
        """
        if prefix == "*":
            pattern = "cache:*"
        else:
            pattern = f"cache:{prefix}:*"

        self.logger.debug("Starting cache invalidation by pattern: %s", pattern)

        deleted_count = 0
        cursor = 0
        start_time = time.time()

        try:
            while True:
                if time.time() - start_time > timeout_seconds:  # pragma: no cover
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
