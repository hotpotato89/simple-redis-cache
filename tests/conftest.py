from fakeredis import FakeRedis as SyncFakeRedis
from fakeredis.aioredis import FakeRedis as AsyncFakeRedis
import pytest

from src.simple_redis_cache.asyncio.cache import Cache as AsyncCache
from src.simple_redis_cache.sync.cache import Cache as SyncCache


@pytest.fixture()
async def async_fakeredis_client() -> AsyncFakeRedis:
    return AsyncFakeRedis()


@pytest.fixture()
def sync_fakeredis_client() -> SyncFakeRedis:
    return SyncFakeRedis()


@pytest.fixture()
async def fake_async_cache(async_fakeredis_client: AsyncFakeRedis) -> AsyncCache:
    return AsyncCache(async_fakeredis_client)


@pytest.fixture()
def fake_sync_cache(sync_fakeredis_client: SyncFakeRedis) -> SyncCache:
    return SyncCache(sync_fakeredis_client)
