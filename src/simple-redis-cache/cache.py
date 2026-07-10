from redis.asyncio import Redis


class Cache:
    def __init__(self, redis_client: Redis) -> None:
        self.redis_client = redis_client


    
