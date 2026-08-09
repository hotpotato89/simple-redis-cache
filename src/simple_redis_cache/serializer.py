# simple_redis_cache/serializer.py
import json
import pickle
from typing import Any

from simple_redis_cache.encoder import CustomJSONEncoder


class Serializer:
    """Отвечает за сериализацию/десериализацию данных для Redis."""

    NULL_MARKER = b"__NULL__"
    PICKLE_PREFIX = b"PICKLE:"
    JSON_ENCODER = CustomJSONEncoder

    @classmethod
    def dumps(cls, value: Any, use_pickle: bool = False) -> bytes:
        """
        Сериализует значение в байты.

        Args:
            value: Любое Python-значение.
            use_pickle: Использовать pickle вместо JSON.

        Returns:
            Байтовое представление для сохранения в Redis.
        """
        if value is None:
            return cls.NULL_MARKER

        if use_pickle:
            return cls.PICKLE_PREFIX + pickle.dumps(value)

        return json.dumps(value, cls=cls.JSON_ENCODER).encode("utf-8")

    @classmethod
    def loads(cls, data: bytes) -> Any:
        """
        Десериализует байты обратно в Python-объект.

        Args:
            data: Байты из Redis.

        Returns:
            Восстановленный Python-объект.

        Raises:
            ValueError: Если данные имеют неизвестный формат.
        """
        if data == cls.NULL_MARKER:
            return None

        if data.startswith(cls.PICKLE_PREFIX):
            return pickle.loads(data[len(cls.PICKLE_PREFIX) :])

        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to deserialize data: {data[:50]}...") from exc
