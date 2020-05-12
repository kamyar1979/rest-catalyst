from typing import TypeVar, Generic, Type, Optional

from catalyst.utils import dict_to_object
from redis import StrictRedis
import aioredis
import umsgpack
from dataclasses import dataclass

T = TypeVar('T', object, dataclass)
async_redis: Optional[aioredis.Redis] = None
redis: Optional[StrictRedis] = None


def init_cache_sync(uri: str, db: int):
    global redis
    redis = StrictRedis.from_url(uri, db)


async def init_cache(uri: str, db: int):
    global async_redis
    async_redis = aioredis.create_redis_pool(uri, db=db)


async def get_cache_item(key: str, t: Type[T]) -> T:
    result = await async_redis.get(key, encoding='utf-8')
    return dict_to_object(umsgpack.loads(result), t)


async def set_cache_item(key: str, obj: T, duration: int):
    data = umsgpack.dumps(obj.to_dict())
    await async_redis.setex(key, duration, data)


def get_cache_item_sync(key: str, t: Type[T]) -> Generic[T]:
    result = redis.get(key)
    return dict_to_object(umsgpack.loads(result), t)


def set_cache_item_sync(key: str, obj: T, duration: int):
    data = umsgpack.dumps(obj.to_dict())
    redis.setex(key, duration, data)
