# simple-redis-cache

![PyPI](https://img.shields.io/badge/PyPI-simple--redis--cache-3776AB?logo=pypi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-8.0-DC382D?logo=redis&logoColor=white)
![uv](https://img.shields.io/badge/uv-0.6-blue?logo=python&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-9.1-blue?logo=pytest&logoColor=white)

Простой инструмент для кэширования асинхронных и синхронных функций в Redis.
1. [Документация]( https://hotpotato89.github.io/simple-redis-cache/)
2. [Ссылка на `PyPI`](https://pypi.org/project/simple-redis-cache/)

## Особенности

- **Автоматическая генерация ключей** — ключи создаются на основе имени функции и аргументов
- **Инвалидация по префиксу** — очищайте кэш группами
- **Кастомный JSON-энкодер** — поддерживает `datetime`, `Decimal`, `UUID`, Pydantic-модели
- **Устойчивость к ошибкам** — ошибки Redis не ломают приложение
- **Гибкая настройка** — можно передать свой логгер
- **sync/async поддержка** — можно использовать как для **синхронных**, так и для **асинхронных** функций
- **100% покрытие** - полная уверенность в коде
- **100% `docstrings`** - полная документация функций



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