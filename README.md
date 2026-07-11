# simple-redis-cache

[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://hotpotato89.github.io/simple-redis-cache/coverage/)
[![PyPI version](https://badge.fury.io/py/simple-redis-cache.svg)](https://badge.fury.io/py/simple-redis-cache)

Простой инструмент для кэширования асинхронных и синхронных функций в Redis.

## Особенности

- **Автоматическая генерация ключей** — ключи создаются на основе имени функции и аргументов
- **Инвалидация по префиксу** — очищайте кэш группами
- **Кастомный JSON-энкодер** — поддерживает `datetime`, `Decimal`, `UUID`, Pydantic-модели
- **Устойчивость к ошибкам** — ошибки Redis не ломают приложение
- **Гибкая настройка** — можно передать свой логгер
- **sync/async поддержка** — можно использовать как для **синхронных**, так и для **асинхронных** функций
- **100% покрытие** - полная уверенность в коде



## Установка

```bash
pip install simple-redis-cache
```

## Использование:

```python
from simple_redis_cache.sync import Cache  # Синхронный
```

```python
from simple_redis_cache.asyncio import Cache  # Асинхронный
```

## Пример

```python
from redis.asyncio import Redis
from simple_redis_cache import Cache

redis = Redis()
cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

# Первый вызов — вычисляется, второй — из кэша
r1 = await get_user(1)
r2 = await get_user(1)

# Одинаковый результат
print(r1 == r2)
```

## Инвалидация
```python
await cache.invalidate_cache(prefix="user")
```

## Лицензия
[**MIT**](LICENSE) 
## Автор
[**hotpotato89**](https://github.com/hotpotato89)