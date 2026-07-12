# Быстрый старт

```bash
pip install simple-redis-cache
```

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
```