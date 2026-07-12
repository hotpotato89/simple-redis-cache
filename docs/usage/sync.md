# Синхронный режим

Для обычных (не асинхронных) проектов: Flask, Django, скрипты.

## Импорт

```python
from simple_redis_cache.sync import Cache
from redis import Redis
```

## Инициализация
```python
redis_client = Redis()
cache_manager = Cache(redis_client)
```

## Кэширование функции

```python
@cache.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}
```

## Инвалидация
```python
cache.invalidate_cache(prefix="user")
```

## Полный пример
```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

print(get_user(1))   # Вычисляется
print(get_user(1))   # Из кэша

cache.invalidate_cache(prefix="user")

print(get_user(1))   # Снова вычисляется
```