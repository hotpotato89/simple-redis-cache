import time
from unittest.mock import patch
import pickle
import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import BaseModel

from simple_redis_cache.sync.cache import Cache


class User(BaseModel):
    id: int
    name: str
    age: int | None = None


class Address(BaseModel):
    city: str
    street: str


class UserWithAddress(BaseModel):
    id: int
    name: str
    address: Address


class UserWithDateTime(BaseModel):
    id: int
    created_at: datetime.datetime


class TestSyncCacheDecorator:
    def test_cache_hit(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        result1 = test_func(5)
        assert result1 == 10

        result2 = test_func(5)
        assert result2 == 10

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_different_args(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)
        test_func(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

    def test_cache_none(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int):
            if x == 0:
                return None
            return x * 2

        result = test_func(0)
        assert result is None

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        cached = fake_sync_cache.redis_client.get(keys[0])
        assert cached == b"__NULL__"

    def test_cache_ttl(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=1)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        time.sleep(1.5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    def test_cache_prefix(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="user")
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:user:*")
        assert len(keys) == 1

    def test_cache_default_ttl(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=10)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        ttl = fake_sync_cache.redis_client.ttl(keys[0])
        assert ttl == 10

    def test_cache_kwargs(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(a: int, b: int) -> int:
            return a + b

        test_func(a=1, b=2)
        test_func(b=2, a=1)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_method(self, fake_sync_cache: Cache) -> None:
        class TestClass:
            def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        decorated = fake_sync_cache.cache(ttl=60)(obj.method)

        decorated(10)
        decorated(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_redis_error(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        original_get = fake_sync_cache.redis_client.get

        def failing_get(*args, **kwargs):
            raise Exception("Redis connection error")

        fake_sync_cache.redis_client.get = failing_get

        result = test_func(5)
        assert result == 10

        fake_sync_cache.redis_client.get = original_get

    def test_cache_async_function_error(self, fake_sync_cache: Cache) -> None:
        async def async_func():
            return 42

        with pytest.raises(TypeError) as exc:
            fake_sync_cache.cache(ttl=60)(async_func)

        assert "sync" in str(exc.value)


class TestSyncCacheInvalidation:
    def test_invalidate_by_prefix(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="user")
        def user_func(x: int) -> int:
            return x * 2

        @fake_sync_cache.cache(ttl=60, prefix="admin")
        def admin_func(x: int) -> int:
            return x * 2

        user_func(5)
        admin_func(10)

        user_keys = fake_sync_cache.redis_client.keys("cache:user:*")
        admin_keys = fake_sync_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 1
        assert len(admin_keys) == 1

        deleted = fake_sync_cache.invalidate_cache(prefix="user")
        assert deleted == 1

        user_keys = fake_sync_cache.redis_client.keys("cache:user:*")
        admin_keys = fake_sync_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 0
        assert len(admin_keys) == 1

    def test_invalidate_all(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="test")
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)
        test_func(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = fake_sync_cache.invalidate_cache()
        assert deleted == 2

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    def test_invalidate_timeout(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="test")
        def test_func(x: int) -> int:
            return x * 2

        for i in range(10):
            test_func(i)

        def slow_scan(*args, **kwargs):
            time.sleep(1)
            return 0, []

        with patch.object(fake_sync_cache.redis_client, "scan", side_effect=slow_scan):
            deleted = fake_sync_cache.invalidate_cache(prefix="test", timeout_seconds=1)
            assert deleted == 0

    def test_invalidate_empty(self, fake_sync_cache: Cache) -> None:
        deleted = fake_sync_cache.invalidate_cache(prefix="nonexistent")
        assert deleted == 0

    def test_invalidate_no_prefix(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)
        test_func(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = fake_sync_cache.invalidate_cache()
        assert deleted == 2

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 0


class TestSyncCachePickle:
    def test_pickle_simple_object(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_data() -> dict:
            return {"id": 1, "name": "Alice"}

        result1 = get_data()
        assert result1 == {"id": 1, "name": "Alice"}

        result2 = get_data()
        assert result2 == {"id": 1, "name": "Alice"}

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        cached = fake_sync_cache.redis_client.get(keys[0])
        assert cached.startswith(b"PICKLE:")  # type: ignore
        data = pickle.loads(cached[7:])  # type: ignore
        assert data == {"id": 1, "name": "Alice"}

    def test_pickle_custom_class(self, fake_sync_cache: Cache) -> None:
        class MyClass:
            def __init__(self, x: int, y: str):
                self.x = x
                self.y = y

            def __eq__(self, other):
                return (
                    isinstance(other, MyClass)
                    and self.x == other.x
                    and self.y == other.y
                )

        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_object() -> MyClass:
            return MyClass(42, "hello")

        result1 = get_object()
        assert isinstance(result1, MyClass)
        assert result1.x == 42
        assert result1.y == "hello"

        result2 = get_object()
        assert isinstance(result2, MyClass)
        assert result2.x == 42
        assert result2.y == "hello"

    def test_pickle_datetime(self, fake_sync_cache: Cache) -> None:
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)

        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_datetime() -> datetime.datetime:
            return dt

        result1 = get_datetime()
        assert result1 == dt

        result2 = get_datetime()
        assert result2 == dt

    def test_pickle_decimal(self, fake_sync_cache: Cache) -> None:
        dec = Decimal("19.99")

        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_decimal() -> Decimal:
            return dec

        result1 = get_decimal()
        assert result1 == dec

        result2 = get_decimal()
        assert result2 == dec

    def test_pickle_uuid(self, fake_sync_cache: Cache) -> None:
        uid = UUID("123e4567-e89b-12d3-a456-426614174000")

        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_uuid() -> UUID:
            return uid

        result1 = get_uuid()
        assert result1 == uid

        result2 = get_uuid()
        assert result2 == uid

    def test_pickle_pydantic_model(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_user(user_id: int) -> User:
            return User(id=user_id, name=f"User_{user_id}", age=25)

        user1 = get_user(1)
        assert isinstance(user1, User)
        assert user1.id == 1
        assert user1.name == "User_1"
        assert user1.age == 25

        user2 = get_user(1)
        assert isinstance(user2, User)
        assert user2.id == 1
        assert user2.name == "User_1"
        assert user2.age == 25

        keys = fake_sync_cache.redis_client.keys("cache:*")
        cached = fake_sync_cache.redis_client.get(keys[0])
        assert cached.startswith(b"PICKLE:")  # type: ignore
        data = pickle.loads(cached[7:])  # type: ignore
        assert isinstance(data, User)
        assert data.id == 1

    def test_pickle_nested_models(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_user(user_id: int) -> UserWithAddress:
            return UserWithAddress(
                id=user_id,
                name=f"User_{user_id}",
                address=Address(city="Moscow", street="Tverskaya"),
            )

        user1 = get_user(1)
        assert isinstance(user1, UserWithAddress)
        assert isinstance(user1.address, Address)
        assert user1.address.city == "Moscow"

        user2 = get_user(1)
        assert isinstance(user2, UserWithAddress)
        assert isinstance(user2.address, Address)
        assert user2.address.city == "Moscow"

    def test_pickle_with_none(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, use_pickle=True)
        def get_none() -> None:
            return None

        result1 = get_none()
        assert result1 is None

        result2 = get_none()
        assert result2 is None

        keys = fake_sync_cache.redis_client.keys("cache:*")
        cached = fake_sync_cache.redis_client.get(keys[0])
        assert cached == b"__NULL__"

    def test_pickle_mixed_with_json(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="json")
        def json_func() -> dict:
            return {"type": "json", "value": 123}

        @fake_sync_cache.cache(ttl=60, prefix="pickle", use_pickle=True)
        def pickle_func() -> dict:
            return {"type": "pickle", "value": 456}

        json_func()
        pickle_func()

        json_keys = fake_sync_cache.redis_client.keys("cache:json:*")
        pickle_keys = fake_sync_cache.redis_client.keys("cache:pickle:*")

        assert len(json_keys) == 1
        assert len(pickle_keys) == 1

        json_cached = fake_sync_cache.redis_client.get(json_keys[0])
        pickle_cached = fake_sync_cache.redis_client.get(pickle_keys[0])

        assert not json_cached.startswith(b"PICKLE:")  # type: ignore
        assert pickle_cached.startswith(b"PICKLE:")  # type: ignore

        result1 = json_func()
        result2 = pickle_func()

        assert result1 == {"type": "json", "value": 123}
        assert result2 == {"type": "pickle", "value": 456}

    def test_pickle_with_ttl(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=1, use_pickle=True)
        def test_func() -> dict:
            return {"data": "test"}

        test_func()
        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        time.sleep(1.5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    def test_pickle_with_prefix(self, fake_sync_cache: Cache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="pickle_test", use_pickle=True)
        def test_func() -> dict:
            return {"data": "test"}

        test_func()

        keys = fake_sync_cache.redis_client.keys("cache:pickle_test:*")
        assert len(keys) == 1

        deleted = fake_sync_cache.invalidate_cache(prefix="pickle_test")
        assert deleted == 1

        keys = fake_sync_cache.redis_client.keys("cache:pickle_test:*")
        assert len(keys) == 0
