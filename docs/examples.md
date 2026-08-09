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
    print(await get_user(1))  # Из БД
    print(await get_user(1))  # Из кэша

    await cache.invalidate_cache(prefix="user")  # Очистка

    print(await get_user(1))  # Снова из БД


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

## Сжатие данных (lz4)

```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)


# Включаем сжатие для больших данных
@cache.cache(ttl=300, prefix="big", compress=True, compress_threshold=2048)
def get_big_data():
    return {"data": "x" * 100000}  # Будет сжато автоматически


data = get_big_data()  # В Redis сохранится сжатая версия
```

## Хранение сложных объектов через pickle

```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)


class User:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


@cache.cache(ttl=60, prefix="user", use_pickle=True)
def get_user(user_id: int) -> User:
    return User(id=user_id, name="Alice")


user = get_user(1)  # Объект сохраняется в Redis через pickle
print(user.name)    # Alice
```

## Не кэшировать None

```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)


@cache.cache(ttl=60, prefix="user", cache_none=False)
def find_user(user_id: int):
    return None  # Не будет сохранено в кэше


result = find_user(1)  # Функция выполнится каждый раз
```

## Синхронный + асинхронный в одном проекте

```python
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from simple_redis_cache.sync import Cache as SyncCache
from simple_redis_cache.asyncio import Cache as AsyncCache

# Синхронная часть
sync_redis = Redis()
sync_cache = SyncCache(sync_redis)

@sync_cache.cache(ttl=60, prefix="sync")
def get_data_sync():
    return {"sync": "data"}

# Асинхронная часть
async_redis = AsyncRedis()
async_cache = AsyncCache(async_redis)

@async_cache.cache(ttl=60, prefix="async")
async def get_data_async():
    return {"async": "data"}
```