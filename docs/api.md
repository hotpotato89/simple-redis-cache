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
def cache(
    self,
    ttl: int,
    prefix: str | None = None,
    use_pickle: bool = False,
    cache_none: bool = True,
    compress: bool = False,
    compress_threshold: int = 1024
) -> Callable
```

#### Аргументы

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `ttl` | `int` | **обязательный** | Время жизни кэша в секундах |
| `prefix` | `str \| None` | `None` | Опциональный префикс для ключа |
| `use_pickle` | `bool` | `False` | Использовать `pickle` для сериализации |
| `cache_none` | `bool` | `True` | Кэшировать значение `None` |
| `compress` | `bool` | `False` | Сжимать данные через lz4 |
| `compress_threshold` | `int` | `1024` | Минимальный размер данных для сжатия (в байтах) |

> ⚠️ **Опасно:** Не используйте `pickle` для недоверенных данных. Это может выполнить произвольный код.

> ⚠️ **Важно:** Не используйте `decode_responses=True` в Redis-клиенте при включённом `use_pickle=True`.

> 💡 **Требование:** Для использования `compress=True` установите `pip install simple-redis-cache[lz4]`.

### `invalidate_cache`

```python
def invalidate_cache(self, prefix: str = "*", timeout_seconds: int = 30) -> int
```
Удаляет все ключи по префиксу.

#### Аргументы

* `prefix` - префикс для удаления. `"*"` - удаляет всё.
* `timeout_seconds` - время, отведенное на выполнение инвалидации.

**Возвращает**: удаленное количество ключей.

---

## `Cache` (асинхронный)

Аналогичный синхронному, но методы асинхронные.

```python
from simple_redis_cache.asyncio import Cache

cache = Cache(redis)


@cache.cache(ttl=60, prefix="user", compress=True)
async def get_user(user_id: int):
    return {"id": user_id}


await cache.invalidate_cache(prefix="user")
```

---

## `Serializer`

Отвечает за сериализацию/десериализацию данных.

### Константы

| Константа | Значение | Описание |
|-----------|----------|----------|
| `NULL_MARKER` | `b"__NULL__"` | Маркер для `None` |
| `PICKLE_PREFIX` | `b"PICKLE:"` | Префикс для pickle-данных |
| `LZ4_PREFIX` | `b"LZ4:"` | Префикс для сжатых данных |
| `COMPRESS_THRESHOLD` | `1024` | Порог сжатия по умолчанию |

### Методы

#### `dumps`

```python
@classmethod
def dumps(
    cls,
    value: Any,
    use_pickle: bool = False,
    compress: bool = False,
    compress_threshold: int = 1024
) -> bytes
```

Сериализует значение в байты.

#### `loads`

```python
@classmethod
def loads(cls, data: bytes) -> Any
```

Десериализует байты обратно в Python-объект.

---

## `CustomJSONEncoder`

Кастомный JSON-энкодер для поддержки дополнительных типов:

| Тип | Формат |
|-----|--------|
| `datetime` | ISO-строка (`2026-08-09T15:30:45`) |
| `date` | ISO-строка (`2026-08-09`) |
| `time` | ISO-строка (`15:30:45.123456`) |
| `timedelta` | Количество секунд (`float`) |
| `Decimal` | Строка (`"99.90"`) |
| `UUID` | Строка (`"550e8400-..."`) |
| Pydantic-модели | `model_dump()` |

### Пример

```python
import json
from datetime import datetime
from decimal import Decimal
from simple_redis_cache.encoder import CustomJSONEncoder

data = {
    "created": datetime.now(),
    "price": Decimal("99.90")
}
json.dumps(data, cls=CustomJSONEncoder)
# '{"created": "2026-08-09T15:30:45", "price": "99.90"}'
```

---

## Исключения

| Исключение | Когда возникает |
|------------|-----------------|
| `TypeError` | Декоратор применён к функции не того типа (sync/async) |
| `ValueError` | Некорректные данные при десериализации |