# Асинхронный режим

Для асинхронных проектов: `FastAPI`, `aiohttp`, `aiogram`.

## Импорт

```python
from simple_redis_cache.asyncio import Cache
from redis.asyncio import Redis
```

## Инициализация

```python
redis_client = Redis()
cache_manager = Cache(redis_client)
```

## Кэширование функции

```python
@cache_manager.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}
```

### Хранение сложных объектов

Для типов, которые не сериализуются в JSON, используйте `pickle`:

> ⚠️ **Опасно:** Не используйте `pickle` для недоверенных данных. Это может выполнить произвольный код.

```python
@cache_manager.cache(ttl=60, prefix="user", use_pickle=True)
async def get_user(user_id: int) -> User:
    return User(id=user_id, name="Alice")
```

### Сжатие данных

Для больших объёмов данных можно включить сжатие через **lz4**.

```python
@cache_manager.cache(ttl=300, prefix="big", compress=True, compress_threshold=2048)
async def get_big_data():
    return {"data": "x" * 100000}
```

> **Требование:** Для использования сжатия установите `simple-redis-cache[lz4]`.  
> Подробнее про установку в [разделе Установка](../installation.md).  
> Все параметры описаны в [API Reference](../api.md).

### Кэширование `None`

По умолчанию `None` кэшируется. Это можно отключить:

```python
@cache_manager.cache(ttl=60, cache_none=False)
async def find_user(email: str) -> dict | None:
    return None  # Не будет сохранено в кэше
```

## Инвалидация

```python
await cache_manager.invalidate_cache(prefix="user")
```

## Полный пример

```python
from redis.asyncio import Redis
from simple_redis_cache.asyncio import Cache

redis = Redis()
cache = Cache(redis)


@cache.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}


print(await get_user(1))  # Вычисляется
print(await get_user(1))  # Из кэша

await cache.invalidate_cache(prefix="user")

print(await get_user(1))  # Снова вычисляется
```