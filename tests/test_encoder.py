# tests/test_encoder.py
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from simple_redis_cache.encoder import CustomJSONEncoder


class TestCustomJSONEncoder:
    """Тесты для кастомного JSON-кодировщика."""

    def test_datetime_serialization(self):
        """Сериализация datetime."""
        dt = datetime(2026, 8, 9, 15, 30, 45)
        result = json.dumps({"created": dt}, cls=CustomJSONEncoder)
        assert result == '{"created": "2026-08-09T15:30:45"}'

    def test_date_serialization(self):
        """Сериализация date."""
        d = date(2026, 8, 9)
        result = json.dumps({"birthday": d}, cls=CustomJSONEncoder)
        assert result == '{"birthday": "2026-08-09"}'

    def test_time_serialization(self):
        """Сериализация time."""
        t = time(15, 30, 45, 123456)
        result = json.dumps({"time": t}, cls=CustomJSONEncoder)
        assert result == '{"time": "15:30:45.123456"}'

    def test_timedelta_serialization(self):
        """Сериализация timedelta."""
        td = timedelta(days=5, hours=3, minutes=30)
        result = json.dumps({"duration": td}, cls=CustomJSONEncoder)
        # 5 дней = 432000 сек + 3 часа = 10800 сек + 30 мин = 1800 сек
        assert result == '{"duration": 444600.0}'

    def test_decimal_serialization(self):
        """Сериализация Decimal (как строка)."""
        price = Decimal("10.50")
        result = json.dumps({"price": price}, cls=CustomJSONEncoder)
        assert result == '{"price": "10.50"}'  # ← строка!

    def test_uuid_serialization(self):
        """Сериализация UUID."""
        uid = uuid4()
        result = json.dumps({"id": uid}, cls=CustomJSONEncoder)
        assert result == f'{{"id": "{uid!s}"}}'

    def test_pydantic_model_serialization(self):
        """Сериализация Pydantic-модели."""
        from pydantic import BaseModel

        class User(BaseModel):
            name: str
            age: int

        user = User(name="Alice", age=30)
        result = json.dumps({"user": user}, cls=CustomJSONEncoder)
        assert result == '{"user": {"name": "Alice", "age": 30}}'

    def test_list_of_mixed_types(self):
        """Сериализация списка с разными типами."""
        dt = datetime(2026, 7, 10, 12, 0, 0)
        data = [dt, "text", 42, Decimal("10.50")]
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert result == '["2026-07-10T12:00:00", "text", 42, "10.50"]'  # ← строка

    def test_nested_structures(self):
        """Сериализация вложенных структур."""
        data = {
            "user": {
                "name": "Alice",
                "balance": Decimal("100.50"),
                "created": date(2024, 1, 1),
            }
        }
        result = json.dumps(data, cls=CustomJSONEncoder)
        # Decimal → строка
        assert (
            result
            == '{"user": {"name": "Alice", "balance": "100.50", "created": "2024-01-01"}}'
        )

    def test_unsupported_type(self):
        """Сериализация неподдерживаемого типа."""

        class Unsupported:
            pass

        with pytest.raises(TypeError) as exc:
            json.dumps({"obj": Unsupported()}, cls=CustomJSONEncoder)
        assert "not JSON serializable" in str(exc.value)
