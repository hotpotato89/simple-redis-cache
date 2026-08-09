# simple_redis_cache/serializer.py
import json
import pickle
from typing import Any

from simple_redis_cache.encoder import CustomJSONEncoder


class Serializer:
    """Отвечает за сериализацию/десериализацию данных для Redis."""

    NULL_MARKER = b"__NULL__"
    PICKLE_PREFIX = b"PICKLE:"
    LZ4_PREFIX = b"LZ4:"
    JSON_ENCODER = CustomJSONEncoder

    COMPRESS_THRESHOLD = 1024

    @classmethod
    def dumps(
        cls,
        value: Any,
        use_pickle: bool = False,
        compress: bool = False,
        compress_threshold: int = COMPRESS_THRESHOLD,
    ) -> bytes:
        """
        Сериализует значение в байты.

        Args:
            value: Любое Python-значение.
            use_pickle: Использовать pickle вместо JSON.
            compress: Сжимать данные через lz4
            compress_threshold: Порог сжатия данныъ в битах

        Returns:
            Байтовое представление для сохранения в Redis.
        """
        if value is None:
            return cls.NULL_MARKER

        if use_pickle:
            data = cls.PICKLE_PREFIX + pickle.dumps(value)
        else:
            data = json.dumps(value, cls=cls.JSON_ENCODER).encode("utf-8")

        if compress and len(data) > compress_threshold:
            return cls._compress_data(data)

        return data

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

        if data.startswith(cls.LZ4_PREFIX):
            data = cls._decompress_data(data)

        if data.startswith(cls.PICKLE_PREFIX):
            return pickle.loads(data[len(cls.PICKLE_PREFIX) :])

        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to deserialize data: {data[:50]}...") from exc

    @classmethod
    def _compress_data(cls, data: bytes) -> bytes:
        """Сжимает данные через lz4"""
        import lz4.frame

        compressed = lz4.frame.compress(data)
        return cls.LZ4_PREFIX + compressed

    @classmethod
    def _decompress_data(cls, data: bytes) -> bytes:
        """Распаковывает данные через lz4"""
        import lz4.frame

        return lz4.frame.decompress(data[len(cls.LZ4_PREFIX) :])
