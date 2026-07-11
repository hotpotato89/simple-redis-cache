import time
from unittest.mock import patch

import pytest

from src.simple_redis_cache.sync.cache import Cache as SyncCache


class TestSyncCacheDecorator:
    def test_cache_hit(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        result1 = test_func(5)
        assert result1 == 10

        result2 = test_func(5)
        assert result2 == 10

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_different_args(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)
        test_func(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 2

    def test_cache_none(self, fake_sync_cache: SyncCache) -> None:
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

    def test_cache_ttl(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=1)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        time.sleep(1.5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 0

    def test_cache_prefix(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=60, prefix="user")
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:user:*")
        assert len(keys) == 1

    def test_cache_default_ttl(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=10)
        def test_func(x: int) -> int:
            return x * 2

        test_func(5)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

        ttl = fake_sync_cache.redis_client.ttl(keys[0])
        assert ttl == 10

    def test_cache_kwargs(self, fake_sync_cache: SyncCache) -> None:
        @fake_sync_cache.cache(ttl=60)
        def test_func(a: int, b: int) -> int:
            return a + b

        test_func(a=1, b=2)
        test_func(b=2, a=1)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_method(self, fake_sync_cache: SyncCache) -> None:
        class TestClass:
            def method(self, x: int) -> int:
                return x * 2

        obj = TestClass()
        decorated = fake_sync_cache.cache(ttl=60)(obj.method)

        decorated(10)
        decorated(10)

        keys = fake_sync_cache.redis_client.keys("cache:*")
        assert len(keys) == 1

    def test_cache_redis_error(self, fake_sync_cache: SyncCache) -> None:
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

    def test_cache_async_function_error(self, fake_sync_cache: SyncCache) -> None:
        async def async_func():
            return 42

        with pytest.raises(TypeError) as exc:
            fake_sync_cache.cache(ttl=60)(async_func)

        assert "sync" in str(exc.value)


class TestSyncCacheInvalidation:
    def test_invalidate_by_prefix(self, fake_sync_cache: SyncCache) -> None:
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

    def test_invalidate_all(self, fake_sync_cache: SyncCache) -> None:
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

    def test_invalidate_timeout(self, fake_sync_cache: SyncCache) -> None:
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

    def test_invalidate_empty(self, fake_sync_cache: SyncCache) -> None:
        deleted = fake_sync_cache.invalidate_cache(prefix="nonexistent")
        assert deleted == 0

    def test_invalidate_no_prefix(self, fake_sync_cache: SyncCache) -> None:
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
