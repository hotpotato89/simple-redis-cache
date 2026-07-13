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

```python
@cache_manager.cache(ttl=60, prefix="user", use_pickle=True)
async def get_user(user_id: int) -> User:
    return User(id=user_id, name="Alice")
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

@cache_manager.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

print(await get_user(1))   # Вычисляется
print(await get_user(1))   # Из кэша

await cache_manager.invalidate_cache(prefix="user")

print(await get_user(1))   # Снова вычисляется
```