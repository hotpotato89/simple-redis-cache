# Примеры

## Синхронный режим с кастомным TTL

```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=3600, prefix="product")
def get_product(product_id: int):
    return {"id": product_id, "name": "Laptop", "price": 999.99}

print(get_product(1))  # 1 час в кэше
```

## Асинхронный режим с инвалидацией

```python
import asyncio
from redis.asyncio import Redis
from simple_redis_cache.asyncio import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

async def main():
    print(await get_user(1))          # Из БД
    print(await get_user(1))          # Из кэша

    await cache.invalidate_cache(prefix="user")  # Очистка

    print(await get_user(1))          # Снова из БД

asyncio.run(main())
```

## Инвалидация нескольких префиксов

```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

@cache.cache(ttl=60, prefix="post")
def get_post(post_id: int):
    return {"id": post_id, "title": "Hello"}

get_user(1)
get_post(1)

cache.invalidate_cache(prefix="user")  # Удалит только кэш пользователей
cache.invalidate_cache(prefix="post")  # Удалит только кэш постов
```

## Использование кастомного логгера

```python
import logging
from redis import Redis
from simple_redis_cache.sync import Cache

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("my_app")

redis = Redis()
cache = Cache(redis, logger=logger)

@cache.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

get_user(1)  # Логи будут выводиться через твой логгер
```