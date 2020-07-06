from collections import Mapping
from typing import TypeVar, Type, Optional, Union, Dict, Any

from catalyst.extensions import to_dict

from catalyst.utils import dict_to_object
from redis import StrictRedis
import aioredis
import umsgpack
from dataclasses import dataclass

T = TypeVar('T', object, dataclass)
async_redis: Optional[aioredis.Redis] = None
redis: Optional[StrictRedis] = None


def is_cache_initialized() -> bool:
    return bool(redis) or bool(async_redis)


def init_cache_sync(uri: str, db: Optional[int] = None):
    global redis
    if uri:
        redis = StrictRedis.from_url(uri, db)


async def init_cache(uri: str, db: Optional[int] = None):
    global async_redis
    if uri:
        async_redis = await aioredis.create_redis_pool(uri, db=db)


async def get_cache_item(key: str,
                         t: Optional[Type[T]] = None) -> Union[None, T, Dict[str, Any]]:
    if await async_redis.exists(key):
        result = await async_redis.get(key)
        if result:
            data = umsgpack.unpackb(result)
            if t:
                return dict_to_object(data, t)
            else:
                return data


async def set_cache_item(key: str, obj: T, duration: int):
    data = to_dict(obj, locale='en-US') if not isinstance(obj, Mapping) else dict(obj)
    await async_redis.setex(key, duration, umsgpack.packb(data))


async def delete_cache_items(wildcard: str):
    items = await async_redis.keys(wildcard)
    if items:
        for key in items:
            await async_redis.delete(key)


def get_cache_item_sync(key: str, t: Optional[Type[T]] = None) -> Union[None, T, Dict[str, Any]]:
    if redis.exists(key):
        result = redis.get(key)
        if result:
            data = umsgpack.unpackb(result)
            if t:
                return dict_to_object(data, t)
            else:
                return data


def set_cache_item_sync(key: str, obj: T, duration: int):
    data = to_dict(obj, locale='en-US') if not isinstance(obj, Mapping) else dict(obj)
    redis.setex(key, duration, umsgpack.packb(data))


def delete_cache_items_sync(wildcard: str):
    items = redis.keys(wildcard)
    if items:
        for key in items:
            redis.delete(key)