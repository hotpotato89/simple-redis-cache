import asyncio
import inspect
from collections.abc import Callable
from functools import wraps
from logging import Logger, getLogger
from typing import ParamSpec, TypeVar, cast

from redis.asyncio import Redis

from simple_redis_cache.key_generator import gen_cache_key
from simple_redis_cache.serializer import Serializer

T = TypeVar("T")
P = ParamSpec("P")


class Cache:
    """
    Класс для кэширования результатов асинхронных функций в Redis.

    Args:
        redis_client: Клиент Redis из `redis.asyncio`.
        logger: Опциональный логгер. Если не передан, создаётся автоматически.

    Example:
        >>> from redis.asyncio import Redis
        >>> from simple_redis_cache.asyncio import Cache
        >>>
        >>> redis = Redis()
        >>> cache = Cache(redis)
        >>>
        >>> @cache.cache(ttl=60, prefix="user")
        >>> async def get_user(user_id: int) -> dict:
        ...     return {"id": user_id, "name": "Alice"}
    """

    __slots__ = ("logger", "redis_client")

    def __init__(
        self,
        redis_client: Redis,
        logger: Logger = getLogger(__name__),
    ) -> None:
        self.redis_client = redis_client
        self.logger = logger

    def cache(
        self,
        ttl: int,
        prefix: str | None = None,
        use_pickle: bool = False,
        cache_none: bool = True,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Декоратор для кэширования асинхронной функции.

        Args:
            ttl: Время жизни кэша в секундах.
            prefix: Опциональный префикс для ключа кэша.
            use_pickle: Использовать pickle в качестве сериализатора.
            cache_none: Определяет, нужно ли кэшировать результат, если функция вернула `None`.
                - По умолчанию `True` (для обратной совместимости): `None` кэшируется как специальное значение.
                - Если `False`, то `None` **не** будет сохранён в кэше. Это полезно для случаев, когда
                  результат функции может отсутствовать и вы хотите позволить функции выполниться снова,
                  чтобы получить актуальные данные.

        Returns:
            Декоратор, оборачивающий функцию с кэшированием.

        Raises:
            TypeError: Если функция синхронная, а не асинхронная.

        Example:
            >>> # Кэшировать результат, даже если он `None`
            >>> @cache.cache(ttl=60, prefix="user")
            >>> async def get_user(user_id: int) -> dict | None:
            ...     return None
            >>>
            >>> # Не кэшировать результат, если он `None`
            >>> @cache.cache(ttl=60, prefix="user", cache_none=False)
            >>> async def find_user(email: str) -> dict | None:
            ...     # Если пользователь не найден, функция вернёт None, но это не будет сохранено в кэше
            ...     return None
        """

        def wrapper(func: Callable[P, T]) -> Callable[P, T]:
            if not inspect.iscoroutinefunction(func):
                raise TypeError(
                    f"@cache can only be used on async functions. "
                    f"'{func.__name__}' is sync."
                )

            @wraps(func)
            async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
                cache_key = gen_cache_key(func, args, kwargs, prefix)

                # --- GET ---
                try:
                    cached = await self.redis_client.get(cache_key)
                    if cached is not None:
                        self.logger.debug("Cache HIT: %s", cache_key)
                        if isinstance(cached, str):
                            cached = cached.encode("utf-8")
                        return Serializer.loads(cached)
                except Exception as exc:
                    self.logger.warning(
                        "Failed cache get for key: %s",
                        cache_key,
                        exc_info=exc,
                    )

                # --- Вычисляем результат ---
                result = await func(*args, **kwargs)

                # --- SET ---
                if result is not None or cache_none:
                    try:
                        data_to_cache = Serializer.dumps(result, use_pickle=use_pickle)
                        await self.redis_client.set(cache_key, data_to_cache, ex=ttl)
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

    async def invalidate_cache(
        self,
        prefix: str = "*",
        timeout_seconds: int = 30,
    ) -> int:
        """
        Удаляет все ключи кэша по префиксу.

        Args:
            prefix: Префикс для удаления. Если `"*"` — удаляет все ключи.
            timeout_seconds: Максимальное время выполнения операции (сек).

        Returns:
            Количество удалённых ключей.

        Example:
            >>> await cache.invalidate_cache(prefix="user")
            42
        """
        if prefix == "*":
            pattern = "cache:*"
        else:
            pattern = f"cache:{prefix}:*"

        self.logger.debug(
            "Starting cache invalidation by pattern: %s",
            pattern,
        )

        deleted_count = 0
        cursor = 0
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                if (
                    asyncio.get_event_loop().time() - start_time > timeout_seconds
                ):  # pragma: no cover
                    self.logger.warning(
                        "Cache invalidation timed out (%s)",
                        timeout_seconds,
                    )
                    break

                cursor, keys = await self.redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100,
                )

                if keys:
                    await self.redis_client.delete(*keys)
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
