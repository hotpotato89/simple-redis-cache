import hashlib
import json

from redis.asyncio import Redis

from src.simple_redis_cache.encoder import CustomJSONEncoder


class Cache:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client

    def _gen_cache_key(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        prefix: str | None = None,
    ) -> str:
        cleaned_args = args[1:] if args and hasattr(args[0], "__class__") else args
        sorted_kwargs = dict(sorted(kwargs.items()))

        data = {
            "func_name": func_name,
            "args": cleaned_args,
            "kwargs": sorted_kwargs,
        }

        key_hash = hashlib.sha256(
            json.dumps(data, cls=CustomJSONEncoder, sort_keys=True).encode()
        ).hexdigest()

        base_key = f"cache:{key_hash}"
        if prefix:
            return f"cache:{prefix}:{key_hash}"
        return base_key

