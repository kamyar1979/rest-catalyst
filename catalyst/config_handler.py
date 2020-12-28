from http import HTTPStatus
from typing import Optional, TypeVar, Type, Dict, FrozenSet, Any

import aioredis
from redis import StrictRedis
import requests
import aiohttp


T = TypeVar('T')
default_configuration: Dict[str, Any]

async def load_default_config(url: str, keys: FrozenSet[str]):
    global default_configuration
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        response = await session.get(url)
        if response.status == HTTPStatus.OK:
            data = await response.json()
            default_configuration = {k: data.get(k) for k in keys}

def load_default_config_sync(url: str, keys: FrozenSet[str]):
    global default_configuration
    response = requests.get(url)
    if response.status_code == HTTPStatus.OK:
        data = response.json()
        default_configuration = {k: data.get(k) for k in keys}


def init_config_sync(uri: str, db: Optional[int] = None):
    global redis
    if uri:
        redis = StrictRedis.from_url(uri, db)


async def init_config(uri: str, db: Optional[int] = None):
    global async_redis
    if uri:
        async_redis = await aioredis.create_redis_pool(uri, db=db)


async def get_config_value(key: str, t: Type[T] = str) -> T:
    value = await async_redis.get(key)
    if value:
        return t(value)
    elif key in default_configuration:
        value = default_configuration[key]
        await async_redis.set(key, value)
        return value


def get_config_value_sync(key: str, t: Type[T] = str) -> T:
    value = redis.get(key)
    if value:
        return t(value)
    elif key in default_configuration:
        value = default_configuration[key]
        redis.set(key, value)
        return value
