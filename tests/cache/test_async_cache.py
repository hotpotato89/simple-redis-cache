import asyncio
from unittest.mock import patch
import pickle
import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import BaseModel

from simple_redis_cache.asyncio.cache import Cache


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


class TestCacheDecorator:
    async def test_cache_hit(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        result1 = await test_func(5)
        assert result1 == 10

        result2 = await test_func(5)
        assert result2 == 10

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_different_args(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

    async def test_cache_none(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(x: int):
            if x == 0:
                return None
            return x * 2

        result = await test_func(0)
        assert result is None

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        cached = await fake_async_cache.redis_client.get(keys[0])
        assert cached == b"__NULL__"

    async def test_cache_ttl(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=1)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        await asyncio.sleep(1.5)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    async def test_cache_prefix(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="user")
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_async_cache.redis_client.keys("cache:user:*")
        assert len(keys) == 1

    async def test_cache_default_ttl(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=10)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        ttl = await fake_async_cache.redis_client.ttl(keys[0])
        assert ttl == 10

    async def test_cache_kwargs(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(a: int, b: int) -> int:
            return a + b

        await test_func(a=1, b=2)
        await test_func(b=2, a=1)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_method(self, fake_async_cache: Cache) -> None:
        class TestClass:
            async def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        decorated = fake_async_cache.cache(ttl=60)(obj.method)

        await decorated(10)
        await decorated(10)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_redis_error(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        original_get = fake_async_cache.redis_client.get

        async def failing_get(*args, **kwargs):
            raise Exception("Redis connection error")

        fake_async_cache.redis_client.get = failing_get

        result = await test_func(5)
        assert result == 10

        fake_async_cache.redis_client.get = original_get

    def test_cache_sync_function_error(self, fake_async_cache: Cache) -> None:
        def sync_func():
            return 42

        with pytest.raises(TypeError) as exc:
            fake_async_cache.cache(ttl=60)(sync_func)

        assert "async" in str(exc.value)


class TestCacheInvalidation:
    async def test_invalidate_by_prefix(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="user")
        async def user_func(x: int) -> int:
            return x * 2

        @fake_async_cache.cache(ttl=60, prefix="admin")
        async def admin_func(x: int) -> int:
            return x * 2

        await user_func(5)
        await admin_func(10)

        user_keys = await fake_async_cache.redis_client.keys("cache:user:*")
        admin_keys = await fake_async_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 1
        assert len(admin_keys) == 1

        deleted = await fake_async_cache.invalidate_cache(prefix="user")
        assert deleted == 1

        user_keys = await fake_async_cache.redis_client.keys("cache:user:*")
        admin_keys = await fake_async_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 0
        assert len(admin_keys) == 1

    async def test_invalidate_all(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="test")
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = await fake_async_cache.invalidate_cache()
        assert deleted == 2

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    async def test_invalidate_timeout(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="test")
        async def test_func(x: int) -> int:
            return x * 2

        for i in range(10):
            await test_func(i)

        async def slow_scan(*args, **kwargs):
            await asyncio.sleep(1)
            return 0, []

        with patch.object(fake_async_cache.redis_client, "scan", side_effect=slow_scan):
            deleted = await fake_async_cache.invalidate_cache(
                prefix="test", timeout_seconds=1
            )
            assert deleted == 0

    async def test_invalidate_empty(self, fake_async_cache: Cache) -> None:
        deleted = await fake_async_cache.invalidate_cache(prefix="nonexistent")
        assert deleted == 0

    async def test_invalidate_no_prefix(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = await fake_async_cache.invalidate_cache()
        assert deleted == 2

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 0


class TestCachePickle:
    async def test_pickle_simple_object(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_data() -> dict:
            return {"id": 1, "name": "Alice"}

        result1 = await get_data()
        assert result1 == {"id": 1, "name": "Alice"}

        result2 = await get_data()
        assert result2 == {"id": 1, "name": "Alice"}

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        cached = await fake_async_cache.redis_client.get(keys[0])
        assert cached.startswith(b"PICKLE:")  # type: ignore
        data = pickle.loads(cached[7:])  # type: ignore
        assert data == {"id": 1, "name": "Alice"}

    async def test_pickle_custom_class(self, fake_async_cache: Cache) -> None:
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

        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_object() -> MyClass:
            return MyClass(42, "hello")

        result1 = await get_object()
        assert isinstance(result1, MyClass)
        assert result1.x == 42
        assert result1.y == "hello"

        result2 = await get_object()
        assert isinstance(result2, MyClass)
        assert result2.x == 42
        assert result2.y == "hello"

    async def test_pickle_datetime(self, fake_async_cache: Cache) -> None:
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)

        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_datetime() -> datetime.datetime:
            return dt

        result1 = await get_datetime()
        assert result1 == dt

        result2 = await get_datetime()
        assert result2 == dt

    async def test_pickle_decimal(self, fake_async_cache: Cache) -> None:
        dec = Decimal("19.99")

        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_decimal() -> Decimal:
            return dec

        result1 = await get_decimal()
        assert result1 == dec

        result2 = await get_decimal()
        assert result2 == dec

    async def test_pickle_uuid(self, fake_async_cache: Cache) -> None:
        uid = UUID("123e4567-e89b-12d3-a456-426614174000")

        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_uuid() -> UUID:
            return uid

        result1 = await get_uuid()
        assert result1 == uid

        result2 = await get_uuid()
        assert result2 == uid

    async def test_pickle_pydantic_model(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_user(user_id: int) -> User:
            return User(id=user_id, name=f"User_{user_id}", age=25)

        user1 = await get_user(1)
        assert isinstance(user1, User)
        assert user1.id == 1
        assert user1.name == "User_1"
        assert user1.age == 25

        user2 = await get_user(1)
        assert isinstance(user2, User)
        assert user2.id == 1
        assert user2.name == "User_1"
        assert user2.age == 25

        keys = await fake_async_cache.redis_client.keys("cache:*")
        cached = await fake_async_cache.redis_client.get(keys[0])
        assert cached.startswith(b"PICKLE:")  # type: ignore
        data = pickle.loads(cached[7:])  # type: ignore
        assert isinstance(data, User)
        assert data.id == 1

    async def test_pickle_nested_models(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_user(user_id: int) -> UserWithAddress:
            return UserWithAddress(
                id=user_id,
                name=f"User_{user_id}",
                address=Address(city="Moscow", street="Tverskaya"),
            )

        user1 = await get_user(1)
        assert isinstance(user1, UserWithAddress)
        assert isinstance(user1.address, Address)
        assert user1.address.city == "Moscow"

        user2 = await get_user(1)
        assert isinstance(user2, UserWithAddress)
        assert isinstance(user2.address, Address)
        assert user2.address.city == "Moscow"

    async def test_pickle_with_none(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, use_pickle=True)
        async def get_none() -> None:
            return None

        result1 = await get_none()
        assert result1 is None

        result2 = await get_none()
        assert result2 is None

        keys = await fake_async_cache.redis_client.keys("cache:*")
        cached = await fake_async_cache.redis_client.get(keys[0])
        assert cached == b"__NULL__"

    async def test_pickle_mixed_with_json(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="json")
        async def json_func() -> dict:
            return {"type": "json", "value": 123}

        @fake_async_cache.cache(ttl=60, prefix="pickle", use_pickle=True)
        async def pickle_func() -> dict:
            return {"type": "pickle", "value": 456}

        await json_func()
        await pickle_func()

        json_keys = await fake_async_cache.redis_client.keys("cache:json:*")
        pickle_keys = await fake_async_cache.redis_client.keys("cache:pickle:*")

        assert len(json_keys) == 1
        assert len(pickle_keys) == 1

        json_cached = await fake_async_cache.redis_client.get(json_keys[0])
        pickle_cached = await fake_async_cache.redis_client.get(pickle_keys[0])

        assert not json_cached.startswith(b"PICKLE:")  # type: ignore
        assert pickle_cached.startswith(b"PICKLE:")  # type: ignore

        result1 = await json_func()
        result2 = await pickle_func()

        assert result1 == {"type": "json", "value": 123}
        assert result2 == {"type": "pickle", "value": 456}

    async def test_pickle_with_ttl(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=1, use_pickle=True)
        async def test_func() -> dict:
            return {"data": "test"}

        await test_func()
        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        await asyncio.sleep(1.5)

        keys = await fake_async_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    async def test_pickle_with_prefix(self, fake_async_cache: Cache) -> None:
        @fake_async_cache.cache(ttl=60, prefix="pickle_test", use_pickle=True)
        async def test_func() -> dict:
            return {"data": "test"}

        await test_func()

        keys = await fake_async_cache.redis_client.keys("cache:pickle_test:*")
        assert len(keys) == 1

        deleted = await fake_async_cache.invalidate_cache(prefix="pickle_test")
        assert deleted == 1

        keys = await fake_async_cache.redis_client.keys("cache:pickle_test:*")
        assert len(keys) == 0
