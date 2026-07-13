# simple-redis-cache

Простой декоратор для кэширования в Redis.

## Быстрый старт

```python
from redis.asyncio import Redis
from simple_redis_cache.asyncio import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}
```

## Возможности

* Автоматическая генерация ключей на основе имени функции и аргументов
* Инвалидация по префиксу для массовой очистки
* Поддержка синхронного и асинхронного кода
* Гибкая сериализация: JSON по умолчанию или Pickle для сложных объектов
* Встроенная поддержка `datetime`, `Decimal`, `UUID`, `Pydantic-моделей`
* Устойчивость к ошибкам Redis — сбои не ломают приложение

## Разделы

* [Установка](installation.md)
* [Синхронный режим](usage/sync.md)
* [Асинхронный режим](usage/async.md)
* [API Reference](api.md)
