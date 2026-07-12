import hashlib
import inspect
import json
from typing import Callable

from simple_redis_cache.encoder import CustomJSONEncoder


def clean_args(args: tuple, func: Callable) -> tuple:
    """
    Удаляет первый аргумент, если он является `self`, `cls` или `mcs`.

    Это необходимо для методов классов, чтобы `self`/`cls` не влияли на ключ кэша.

    Args:
        args: Кортеж аргументов, переданных в функцию.
        func: Функция, для которой проверяются аргументы.

    Returns:
        Кортеж аргументов без `self`/`cls`/`mcs`, если они были первыми.

    Example:
        >>> class Test:
        ...     def method(self, x: int) -> int:
        ...         return x
        >>>
        >>> clean_args((Test(), 5), Test.method)
        (5,)
        >>>
        >>> def func(x: int) -> int:
        ...     return x
        >>>
        >>> clean_args((5,), func)
        (5,)
    """
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
    """
    Генерирует уникальный ключ для кэша на основе функции и её аргументов.

    Ключ формируется из:
        - имени функции
        - позиционных аргументов (без `self`/`cls`)
        - именованных аргументов (отсортированных)

    Все данные хешируются через SHA-256.

    Args:
        func: Функция, для которой генерируется ключ.
        args: Позиционные аргументы функции.
        kwargs: Именованные аргументы функции.
        prefix: Опциональный префикс для ключа.

    Returns:
        Строка с ключом кэша в формате `cache:{prefix}:{hash}` или `cache:{hash}

    Example:
        >>> def get_user(user_id: int, active: bool = True) -> dict:
        ...     return {"id": user_id}
        >>>
        >>> gen_cache_key(get_user, (1,), {"active": True})
        'cache:9f86d081884c7d659a9fe9650f...'
        >>>
        >>> gen_cache_key(get_user, (1,), {"active": True}, prefix="user")
        'cache:user:9f86d081884c7d659a9fe9650f...'
    """
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
