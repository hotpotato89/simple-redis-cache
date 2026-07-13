# API Reference

## `Cache` (синхронный)

### `__init__`

```python
def __init__(self, redis_client: Redis, logger: Logger | None = None) -> None
```
#### Аргументы

* `redis_client` - экзепляр синхронного `Redis`.
* `logger` - опциональный логгер.

### `cache`

```python
def cache(self, ttl: int, prefix: str | None = None, use_pickle: bool = False) -> Callable
```

#### Аргументы

* `ttl` - время жизни кэша в секундах.
* `prefix` - опциональный префикс для ключа.
* `use_pickle` - использовать `pickle` для сериализации.

> Важно: Не используйте decode_responses=True в Redis-клиенте при включённом use_pickle=True.

### `invalidate_cache`

```python
def invalidate_cache(self, prefix: str = "*", timeout_seconds: int = 30) -> int
```
Удаляет все ключи по префиксу.

#### Аргументы

* `prefix` - префикс для удаления. `"*"` - удаляет всё.
* `timeout_seconds` - времяб отведенное на выполнение инвалидации.

**Возвращает**: удаленное количество ключей.

## `Cache` (асинхронный)

Аналогичный, но методы синхронные

```python
from simple_redis_cache.asyncio import Cache

cache = Cache(redis)

@cache.cache(ttl=60, prefix="user")
async def get_user(user_id: int):
    return {"id": user_id}

await cache.invalidate_cache(prefix="user")
```

## `CustomJSONEncoder`

Кастомный JSON-энкодер для поддержки:
* `datetime` -> ISO-строка
* `Decimal` -> float
* `UUID` -> строка
* `Pydantic-модельи` -> `model_dump()`

### Пример

```python
import json
from datetime import datetime
from simple_redis_cache.encoder import CustomJSONEncoder

data = {"created": datetime.now()}
json.dumps(data, cls=CustomJSONEncoder)
```

