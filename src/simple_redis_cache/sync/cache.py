import inspect
import time
from collections.abc import Callable
from functools import wraps
from logging import Logger, getLogger
from typing import ParamSpec, TypeVar, cast

from redis import Redis

from simple_redis_cache.key_generator import gen_cache_key
from simple_redis_cache.serializer import Serializer

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
        compress: bool = False,
        compress_threshold: int = 1024,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Декоратор для кэширования синхронной функции.

        Args:
            ttl: Время жизни кэша в секундах.
            prefix: Опциональный префикс для ключа кэша.
                Пример: `prefix="user"` → ключ будет `cache:user:<hash>`.
            use_pickle: Использовать pickle в качестве сериализатора.
                Включайте, если нужно кэшировать сложные объекты (классы, множества, байты).
                По умолчанию `False` — используется JSON (быстрее и безопаснее).
            cache_none: Определяет, нужно ли кэшировать результат, если функция вернула `None`.
                - `True` (по умолчанию): `None` кэшируется как специальное значение `__NULL__`.
                  При повторном вызове вернётся `None` без выполнения функции.
                - `False`: `None` **не** сохраняется в кэше. Функция будет выполняться каждый раз,
                  пока не вернёт значение, отличное от `None`.
                  Полезно для API/БД-запросов, где `None` означает "не найдено".
            compress: Сжимать данные через lz4 перед сохранением в Redis.
                Требует установки `lz4`: `pip install simple-redis-cache[lz4]`.
                Сжатие применяется только если размер данных превышает `compress_threshold`.
                По умолчанию `False`.
            compress_threshold: Порог сжатия в байтах.
                Данные меньше этого значения не сжимаются.
                По умолчанию `1024` (1KB).

        Returns:
            Декоратор, оборачивающий функцию с кэшированием.

        Raises:
            TypeError: Если функция асинхронная, а не синхронная.

        Example:
            >>> # Базовое кэширование
            >>> @cache.cache(ttl=60, prefix="user")
            >>> def get_user(user_id: int) -> dict:
            ...     return {"id": user_id, "name": "Alice"}
            >>>
            >>> # Кэширование None
            >>> @cache.cache(ttl=60, prefix="user", cache_none=False)
            >>> def find_user(email: str) -> dict | None:
            ...     # Если пользователь не найден, вернётся None, но это не будет сохранено
            ...     return None
            >>>
            >>> # Кэширование с компрессией
            >>> @cache.cache(ttl=300, compress=True, compress_threshold=2048)
            >>> def get_big_data() -> dict:
            ...     return {"large": "x" * 10000}  # Будет сжато
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

                # --- GET ---
                try:
                    cached = self.redis_client.get(cache_key)
                    if cached is not None:
                        self.logger.debug("Cache HIT: %s", cache_key)
                        if isinstance(cached, str):  # pragma: no cover
                            cached = cached.encode("utf-8")
                        return Serializer.loads(cached)
                except Exception as exc:  # pragma: no cover
                    self.logger.warning(
                        "Failed cache get for key: %s",
                        cache_key,
                        exc_info=exc,
                    )

                # --- Вычисляем результат ---
                result = func(*args, **kwargs)

                # --- SET ---
                if result is not None or cache_none:
                    try:
                        data_to_cache = Serializer.dumps(
                            result,
                            use_pickle=use_pickle,
                            compress=compress,
                            compress_threshold=compress_threshold,
                        )
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

    def invalidate_cache(
        self,
        prefix: str = "*",
        timeout_seconds: int = 30,
    ) -> int:
        """
        Удаляет все ключи кэша по префиксу (синхронная версия).

        Использует `SCAN` для безопасного удаления больших объёмов данных без блокировки Redis.

        Args:
            prefix: Префикс для удаления.
                - `"*"` (по умолчанию): удаляет все ключи кэша (паттерн `cache:*`).
                - Любое другое значение: удаляет ключи по паттерну `cache:{prefix}:*`.
            timeout_seconds: Максимальное время выполнения операции в секундах.
                Если операция превысит этот лимит, она прервётся с предупреждением.
                По умолчанию `30` секунд.

        Returns:
            Количество удалённых ключей.

        Raises:
            Exception: Любая ошибка Redis логируется, но не прерывает выполнение.

        Example:
            >>> # Удалить все ключи с префиксом "user"
            >>> cache.invalidate_cache(prefix="user")
            42
            >>>
            >>> # Удалить все ключи кэша
            >>> cache.invalidate_cache()
            157
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
        start_time = time.time()

        try:
            while True:
                if time.time() - start_time > timeout_seconds:  # pragma: no cover
                    self.logger.warning(
                        "Cache invalidation timed out (%s)",
                        timeout_seconds,
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
