import hashlib
import inspect
import json
from typing import Callable

from src.simple_redis_cache.encoder import CustomJSONEncoder


def clean_args(args: tuple, func: Callable) -> tuple:
    """Remove 'self/cls/mcs' from args"""
    if not args:
        return args

    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    if params and params[0] in ("self", "cls", "mcs"):
        return args[1:]

    return args


def gen_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    prefix: str | None = None,
) -> str:
    cleaned_args = clean_args(args, func)
    sorted_kwargs = dict(sorted(kwargs.items()))

    data = {
        "func_name": func.__name__,
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
