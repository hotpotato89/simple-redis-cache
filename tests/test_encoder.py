import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.simple_redis_cache.encoder import CustomJSONEncoder


class TestCustomJSONEncoder:
    def test_datetime_serialization(self):
        dt = datetime(2026, 7, 10, 15, 30, 0)
        result = json.dumps({"date": dt}, cls=CustomJSONEncoder)
        assert result == '{"date": "2026-07-10T15:30:00"}'

    def test_decimal_serialization(self):
        dec = Decimal("10.5")
        result = json.dumps({"price": dec}, cls=CustomJSONEncoder)
        assert result == '{"price": 10.5}'

    def test_uuid_serialization(self):
        uid = uuid4()
        result = json.dumps({"id": uid}, cls=CustomJSONEncoder)
        expected = f'{{"id": "{str(uid)}"}}'
        assert result == expected

    def test_pydantic_model_serialization(self):
        class TestModel:
            def __init__(self, name: str, age: int):
                self.name = name
                self.age = age

            def model_dump(self):
                return {"name": self.name, "age": self.age}

        obj = TestModel("Alice", 30)
        result = json.dumps({"user": obj}, cls=CustomJSONEncoder)
        assert result == '{"user": {"name": "Alice", "age": 30}}'

    def test_dict_with_model_dump(self):
        class TestModel:
            def __init__(self, name: str):
                self.name = name

            def model_dump(self):
                return {"name": self.name}

        obj = TestModel("Bob")
        result = json.dumps({"user": obj}, cls=CustomJSONEncoder)
        assert result == '{"user": {"name": "Bob"}}'

    def test_unknown_type_raises_error(self):
        class UnknownType:
            pass

        obj = UnknownType()
        with pytest.raises(TypeError) as exc:
            json.dumps({"data": obj}, cls=CustomJSONEncoder)
        assert "is not JSON serializable" in str(exc.value)

    def test_none_serialization(self):
        result = json.dumps({"value": None}, cls=CustomJSONEncoder)
        assert result == '{"value": null}'

    def test_list_of_mixed_types(self):
        dt = datetime(2026, 7, 10, 15, 30, 0)
        dec = Decimal("10.5")
        data = [dt, dec, "text", 42]
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert result == '["2026-07-10T15:30:00", 10.5, "text", 42]'

    def test_nested_structures(self):
        dt = datetime(2026, 7, 10, 15, 30, 0)
        data = {
            "user": {"name": "Alice", "created_at": dt, "balance": Decimal("100.50")}
        }
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert (
            result
            == '{"user": {"name": "Alice", "created_at": "2026-07-10T15:30:00", "balance": 100.5}}'
        )
