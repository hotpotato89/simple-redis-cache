# Синхронный режим

Для обычных (не асинхронных) проектов: `Flask`, `Django`, `скрипты`.

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
@cache_manager.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}
```

### Хранение сложных объектов

Для типов, которые не сериализуются в JSON, используйте `pickle`:

```python
@cache_manager.cache(ttl=60, prefix="user", use_pickle=True)
def get_user(user_id: int) -> User:
    return User(id=user_id, name="Alice")
```

## Инвалидация
```python
cache_manager.invalidate_cache(prefix="user")
```

## Полный пример
```python
from redis import Redis
from simple_redis_cache.sync import Cache

redis = Redis()
cache_manager = Cache(redis)

@cache_manager.cache(ttl=60, prefix="user")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

print(get_user(1))   # Вычисляется
print(get_user(1))   # Из кэша

cache_manager.invalidate_cache(prefix="user")

print(get_user(1))   # Снова вычисляется
```