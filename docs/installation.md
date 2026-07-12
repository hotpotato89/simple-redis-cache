# Установка

## Через pip

```bash
pip install simple-redis-cache
```

## Через uv
```bash
uv add simple-redis-cache
```

## Через poetry
```bash
poetry add simple-redis-cache
```

# Требования

 * `Python` >= 3.10
 * `Redis` >= 8.0

# Проверка установки

```python
import simple_redis_cache
print(simple_redis_cache.__version__)
```