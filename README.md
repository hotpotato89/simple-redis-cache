# simple-redis-cache

Простой декоратор для кэширования асинхронных функций в Redis.


## Особенности

- **Автоматическая генерация ключей** — ключи создаются на основе имени функции и аргументов
- **Инвалидация по префиксу** — очищайте кэш группами
- **Кастомный JSON-энкодер** — поддерживает `datetime`, `Decimal`, `UUID`, Pydantic-модели
- **Устойчивость к ошибкам** — ошибки Redis не ломают приложение
- **Гибкая настройка** — можно передать свой логгер



## Установка

```bash
pip install simple-redis-cache
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