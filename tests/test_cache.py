import asyncio
from unittest.mock import patch

import pytest

from src.simple_redis_cache.cache import Cache


class TestCacheDecorator:
    async def test_cache_hit(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        result1 = await test_func(5)
        assert result1 == 10

        result2 = await test_func(5)
        assert result2 == 10

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_different_args(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

    async def test_cache_none(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(x: int):
            if x == 0:
                return None
            return x * 2

        result = await test_func(0)
        assert result is None

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        cached = await fake_cache.redis_client.get(keys[0])
        assert cached == b"__NULL__"

    async def test_cache_ttl(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=1)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        await asyncio.sleep(1.5)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    async def test_cache_prefix(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60, prefix="user")
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_cache.redis_client.keys("cache:user:*")
        assert len(keys) == 1

    async def test_cache_default_ttl(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=10)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        ttl = await fake_cache.redis_client.ttl(keys[0])
        assert ttl == 10

    async def test_cache_kwargs(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(a: int, b: int) -> int:
            return a + b

        await test_func(a=1, b=2)
        await test_func(b=2, a=1)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_method(self, fake_cache: Cache) -> None:
        class TestClass:
            async def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        decorated = fake_cache.cache(ttl=60)(obj.method)

        await decorated(10)
        await decorated(10)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    async def test_cache_redis_error(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        original_get = fake_cache.redis_client.get

        async def failing_get(*args, **kwargs):
            raise Exception("Redis connection error")

        fake_cache.redis_client.get = failing_get

        result = await test_func(5)
        assert result == 10

        fake_cache.redis_client.get = original_get

    def test_cache_sync_function_error(self, fake_cache: Cache) -> None:
        def sync_func():
            return 42

        with pytest.raises(TypeError) as exc:
            fake_cache.cache(ttl=60)(sync_func)

        assert "async" in str(exc.value)


class TestCacheInvalidation:
    async def test_invalidate_by_prefix(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60, prefix="user")
        async def user_func(x: int) -> int:
            return x * 2

        @fake_cache.cache(ttl=60, prefix="admin")
        async def admin_func(x: int) -> int:
            return x * 2

        await user_func(5)
        await admin_func(10)

        user_keys = await fake_cache.redis_client.keys("cache:user:*")
        admin_keys = await fake_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 1
        assert len(admin_keys) == 1

        deleted = await fake_cache.invalidate_cache(prefix="user")
        assert deleted == 1

        user_keys = await fake_cache.redis_client.keys("cache:user:*")
        admin_keys = await fake_cache.redis_client.keys("cache:admin:*")
        assert len(user_keys) == 0
        assert len(admin_keys) == 1

    async def test_invalidate_all(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60, prefix="test")
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = await fake_cache.invalidate_cache()
        assert deleted == 2

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    async def test_invalidate_timeout(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60, prefix="test")
        async def test_func(x: int) -> int:
            return x * 2

        for i in range(10):
            await test_func(i)

        async def slow_scan(*args, **kwargs):
            await asyncio.sleep(1)
            return 0, []

        with patch.object(fake_cache.redis_client, "scan", side_effect=slow_scan):
            deleted = await fake_cache.invalidate_cache(
                prefix="test", timeout_seconds=1
            )
            assert deleted == 0

    async def test_invalidate_empty(self, fake_cache: Cache) -> None:
        deleted = await fake_cache.invalidate_cache(prefix="nonexistent")
        assert deleted == 0

    async def test_invalidate_no_prefix(self, fake_cache: Cache) -> None:
        @fake_cache.cache(ttl=60)
        async def test_func(x: int) -> int:
            return x * 2

        await test_func(5)
        await test_func(10)

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

        deleted = await fake_cache.invalidate_cache()
        assert deleted == 2

        keys = await fake_cache.redis_client.keys("cache:*")
        assert len(keys) == 0
