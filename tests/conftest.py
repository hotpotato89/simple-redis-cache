from fakeredis.aioredis import FakeRedis
import pytest

from src.simple_redis_cache.cache import Cache


@pytest.fixture(scope="session")
async def fakeredis_client() -> FakeRedis:
    return FakeRedis()


@pytest.fixture(scope="session")
async def fake_cache(fakeredis_client: FakeRedis) -> Cache:
    return Cache(fakeredis_client)
