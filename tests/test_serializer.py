from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from simple_redis_cache.encoder import CustomJSONEncoder
from simple_redis_cache.serializer import Serializer


# --- Класс для теста pickle (на уровне модуля) ---
class CustomObject:
    def __init__(self, x: int, y: str):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


class TestSerializer:
    """Тесты для сериализатора."""

    # === Базовые типы ===

    def test_dumps_loads_none(self):
        """Сериализация и десериализация None."""
        dumped = Serializer.dumps(None)
        assert dumped == b"__NULL__"
        assert Serializer.loads(dumped) is None

    def test_dumps_loads_string(self):
        """Сериализация и десериализация строки."""
        data = "Hello, World!"
        dumped = Serializer.dumps(data)
        assert isinstance(dumped, bytes)
        assert Serializer.loads(dumped) == data

    def test_dumps_loads_integer(self):
        """Сериализация и десериализация целого числа."""
        data = 42
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_dumps_loads_float(self):
        """Сериализация и десериализация числа с плавающей точкой."""
        data = 3.14159
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_dumps_loads_boolean(self):
        """Сериализация и десериализация булевых значений."""
        assert Serializer.loads(Serializer.dumps(True)) is True
        assert Serializer.loads(Serializer.dumps(False)) is False

    def test_dumps_loads_list(self):
        """Сериализация и десериализация списка."""
        data = [1, 2, 3, "four", 5.0]
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_dumps_loads_dict(self):
        """Сериализация и десериализация словаря."""
        data = {"name": "Alice", "age": 30, "active": True}
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_dumps_loads_nested(self):
        """Сериализация и десериализация вложенных структур."""
        data = {
            "user": {
                "id": 1,
                "name": "Bob",
                "tags": ["admin", "user"],
            },
            "meta": {"version": 2.0},
        }
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    # === Pickle ===

    def test_dumps_loads_pickle(self):
        """Сериализация через pickle."""
        obj = CustomObject(42, "test")
        dumped = Serializer.dumps(obj, use_pickle=True)

        assert dumped.startswith(b"PICKLE:")
        loaded = Serializer.loads(dumped)
        assert isinstance(loaded, CustomObject)
        assert loaded.x == 42
        assert loaded.y == "test"

    def test_dumps_loads_pickle_set(self):
        """Сериализация множества через pickle."""
        data = {1, 2, 3, 4, 5}
        dumped = Serializer.dumps(data, use_pickle=True)
        assert dumped.startswith(b"PICKLE:")
        loaded = Serializer.loads(dumped)
        assert loaded == data

    def test_dumps_loads_pickle_bytes(self):
        """Сериализация байтов через pickle."""
        data = b"binary data \x00\x01\x02"
        dumped = Serializer.dumps(data, use_pickle=True)
        loaded = Serializer.loads(dumped)
        assert loaded == data

    # === Кастомные типы (CustomJSONEncoder) ===

    def test_dumps_loads_datetime(self):
        """Сериализация datetime."""
        data = datetime(2026, 8, 9, 15, 30, 45)
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data.isoformat()

    def test_dumps_loads_date(self):
        """Сериализация date."""
        data = date(2026, 8, 9)
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data.isoformat()

    def test_dumps_loads_time(self):
        """Сериализация time."""
        data = time(15, 30, 45, 123456)
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data.isoformat()

    def test_dumps_loads_decimal(self):
        """Сериализация Decimal."""
        data = Decimal("123.456789")
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == str(data)

    def test_dumps_loads_uuid(self):
        """Сериализация UUID."""
        data = uuid4()
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == str(data)

    def test_dumps_loads_timedelta(self):
        """Сериализация timedelta."""
        data = timedelta(days=5, hours=3, minutes=30)
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data.total_seconds()

    def test_dumps_loads_complex_dict(self):
        """Сериализация сложного словаря с разными типами."""
        now = datetime.now()
        uid = uuid4()
        data = {
            "name": "Project",
            "created_at": now,
            "uuid": uid,
            "price": Decimal("99.90"),
            "duration": timedelta(hours=2),
            "active": True,
            "tags": ["python", "redis"],
        }
        dumped = Serializer.dumps(data)
        loaded = Serializer.loads(dumped)
        assert loaded["name"] == "Project"
        assert loaded["created_at"] == now.isoformat()
        assert loaded["uuid"] == str(uid)
        assert loaded["price"] == str(Decimal("99.90"))
        assert loaded["duration"] == timedelta(hours=2).total_seconds()
        assert loaded["active"] is True
        assert loaded["tags"] == ["python", "redis"]

    # === Ошибки ===

    def test_loads_invalid_json(self):
        """Десериализация некорректного JSON."""
        with pytest.raises(ValueError) as exc_info:
            Serializer.loads(b"not valid json")
        assert "Failed to deserialize data" in str(exc_info.value)

    def test_loads_invalid_pickle(self):
        """Десериализация некорректного pickle."""
        data = b"PICKLE:not valid pickle"
        with pytest.raises(Exception):  # pickle.UnpicklingError
            Serializer.loads(data)

    def test_loads_empty_bytes(self):
        """Десериализация пустых байтов."""
        with pytest.raises(ValueError):
            Serializer.loads(b"")

    # === Граничные случаи ===

    def test_serializer_with_empty_string(self):
        """Сериализация пустой строки."""
        data = ""
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_serializer_with_empty_dict(self):
        """Сериализация пустого словаря."""
        data = {}
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_serializer_with_empty_list(self):
        """Сериализация пустого списка."""
        data = []
        dumped = Serializer.dumps(data)
        assert Serializer.loads(dumped) == data

    def test_dumps_use_pickle_with_none(self):
        """Pickle с None всё равно использует NULL_MARKER."""
        dumped = Serializer.dumps(None, use_pickle=True)
        assert dumped == b"__NULL__"  # Не PICKLE:None
        assert Serializer.loads(dumped) is None

    def test_serializer_with_bool_values(self):
        """Сериализация булевых значений."""
        for value in [True, False]:
            dumped = Serializer.dumps(value)
            loaded = Serializer.loads(dumped)
            assert loaded == value
            assert isinstance(loaded, bool)

    def test_serializer_with_large_data(self):
        """Сериализация больших объёмов данных."""
        data = {"key": "value" * 1000}
        dumped = Serializer.dumps(data)
        assert len(dumped) > 0
        loaded = Serializer.loads(dumped)
        assert loaded == data

    # === Проверка маркеров ===

    def test_null_marker_constant(self):
        """Проверка константы NULL_MARKER."""
        assert Serializer.NULL_MARKER == b"__NULL__"

    def test_pickle_prefix_constant(self):
        """Проверка константы PICKLE_PREFIX."""
        assert Serializer.PICKLE_PREFIX == b"PICKLE:"

    def test_json_encoder_class(self):
        """Проверка, что используется правильный JSON-кодировщик."""
        assert Serializer.JSON_ENCODER == CustomJSONEncoder

    # === Тесты для компрессии LZ4 ===

    def test_compress_small_data(self):
        """Данные меньше порога не сжимаются."""
        data = {"key": "value"}
        dumped = Serializer.dumps(data, compress=True, compress_threshold=1024)
        assert not dumped.startswith(b"LZ4:")

    def test_compress_large_data(self):
        """Данные больше порога сжимаются."""
        data = {"key": "x" * 10000}
        dumped = Serializer.dumps(data, compress=True, compress_threshold=1024)
        assert dumped.startswith(b"LZ4:")
        loaded = Serializer.loads(dumped)
        assert loaded == data

    def test_compress_with_pickle(self):
        """Сжатие + pickle."""
        data = {"x": 1, "y": 2, "z": "a" * 10000}
        dumped = Serializer.dumps(
            data,
            use_pickle=True,
            compress=True,
            compress_threshold=1024,
        )
        assert dumped.startswith(b"LZ4:")
        loaded = Serializer.loads(dumped)
        assert loaded == data

    def test_compress_with_pickle_and_small_data(self):
        """Сжатие + pickle, но данные меньше порога."""
        data = {"x": 1, "y": 2}
        dumped = Serializer.dumps(
            data,
            use_pickle=True,
            compress=True,
            compress_threshold=1024,
        )
        # Не должно быть сжато (маленький размер)
        assert not dumped.startswith(b"LZ4:")
        loaded = Serializer.loads(dumped)
        assert loaded == data

    def test_compress_with_custom_threshold(self):
        """Сжатие с кастомным порогом."""
        data = {"key": "x" * 500}

        # Порог 100 → сожмётся
        dumped_compressed = Serializer.dumps(
            data, compress=True, compress_threshold=100
        )
        assert dumped_compressed.startswith(b"LZ4:")

        # Порог 1000 → не сожмётся
        dumped_uncompressed = Serializer.dumps(
            data, compress=True, compress_threshold=1000
        )
        assert not dumped_uncompressed.startswith(b"LZ4:")

    def test_compress_none_value(self):
        """Сжатие None — не должно добавлять LZ4 префикс."""
        dumped = Serializer.dumps(None, compress=True)
        assert dumped == b"__NULL__"
        assert Serializer.loads(dumped) is None

    def test_compress_roundtrip_complex_data(self):
        """Полный цикл сжатия и распаковки для сложных данных."""
        now = datetime.now()
        uid = uuid4()
        data = {
            "name": "Project" * 1000,  # Большая строка
            "created_at": now,
            "uuid": uid,
            "price": Decimal("99.90"),
            "duration": timedelta(hours=2),
            "active": True,
            "tags": ["python", "redis"] * 100,  # Большой список
        }

        dumped = Serializer.dumps(data, compress=True, compress_threshold=1024)
        assert dumped.startswith(b"LZ4:")

        loaded = Serializer.loads(dumped)
        assert loaded["name"] == data["name"]
        assert loaded["created_at"] == now.isoformat()
        assert loaded["uuid"] == str(uid)
        assert loaded["price"] == str(Decimal("99.90"))
        assert loaded["duration"] == timedelta(hours=2).total_seconds()
        assert loaded["active"] is True
        assert loaded["tags"] == data["tags"]

    def test_compress_empty_data(self):
        """Сжатие пустых данных."""
        data = {}
        dumped = Serializer.dumps(data, compress=True)
        # Пустой словарь не сжимается (маленький размер)
        assert not dumped.startswith(b"LZ4:")
        loaded = Serializer.loads(dumped)
        assert loaded == data

    def test_loads_compressed_without_lz4(self):
        """Попытка распаковать LZ4-данные когда lz4 не установлен."""
        # Создаём данные с LZ4 префиксом (невалидные)
        data = b"LZ4:invalid_lz4_data"
        with pytest.raises(Exception):  # lz4.frame.decompress выбросит ошибку
            Serializer.loads(data)

    def test_compress_threshold_default(self):
        """Проверка порога сжатия по умолчанию."""
        # Данные чуть больше 1024 байт
        data = {"key": "x" * 1100}
        dumped = Serializer.dumps(data, compress=True)  # threshold по умолчанию 1024
        assert dumped.startswith(b"LZ4:")

        # Данные меньше 1024 байт
        data = {"key": "x" * 100}
        dumped = Serializer.dumps(data, compress=True)
        assert not dumped.startswith(b"LZ4:")

    def test_compress_with_non_bytes_data(self):
        """Сжатие данных, которые не являются байтами."""
        data = {"key": "value" * 1000}
        dumped = Serializer.dumps(data, compress=True, compress_threshold=1024)
        assert dumped.startswith(b"LZ4:")
        loaded = Serializer.loads(dumped)
        assert loaded == data
