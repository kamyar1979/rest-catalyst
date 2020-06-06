from collections import Mapping
from typing import TypeVar, Type, Optional, Union, Dict, Any, Callable

from catalyst.extensions import to_dict

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
    async_redis = await aioredis.create_redis_pool(uri, db=db)


async def get_cache_item(key: str,
                         t: Optional[Type[T]] = None) -> Union[None, T, Dict[str, Any]]:
    if await async_redis.exists(key):
        result = await async_redis.get(key)
        if t:
            print(umsgpack.loads(result))
            return dict_to_object(umsgpack.loads(result), t)
        else:
            return result


async def set_cache_item(key: str, obj: T, duration: int):
    data = umsgpack.dumps(to_dict(obj, locale='en-US') if not isinstance(obj, Mapping) else dict(obj))
    await async_redis.setex(key, duration, data)


def get_cache_item_sync(key: str, t: Optional[Type[T]] = None) -> Union[None, T, Dict[str, Any]]:
    if redis.exists(key):
        result = redis.get(key)
        if t:
            return dict_to_object(umsgpack.loads(result), t)
        else:
            return result


def set_cache_item_sync(key: str, obj: T, duration: int):
    data = umsgpack.dumps(to_dict(obj, locale='en-US') if not isinstance(obj, Mapping) else dict(obj))
    redis.setex(key, duration, data)
