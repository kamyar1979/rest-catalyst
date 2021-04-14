from http import HTTPStatus
from typing import Optional, TypeVar, Type, Dict, FrozenSet, Any

import aioredis
import tomlkit
from redis import StrictRedis
import requests
import aiohttp


T = TypeVar('T')
default_configuration: Dict[str, Any]

async def load_default_config(url: str, keys: Optional[FrozenSet[str]] = None):
    global default_configuration
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        response = await session.get(url)
        if response.status == HTTPStatus.OK:
            data = tomlkit.loads(await response.text())
            default_configuration = {k: data[k]['default'] for k in (keys if keys else data) if k in data}

def load_default_config_sync(url: str, keys: FrozenSet[str]):
    global default_configuration
    response = requests.get(url)
    if response.status_code == HTTPStatus.OK:
        data = tomlkit.loads(response.text)
        default_configuration = {k: data[k]['default'] for k in (keys if keys else data) if k in data}


def init_config_sync(uri: str,
                     db: Optional[int] = None, *,
                     default_config: Optional[str] = None,
                     keys: Optional[FrozenSet[str]] = None):
    global redis
    if uri:
        redis = StrictRedis.from_url(uri, db)
    if default_config:
        load_default_config_sync(default_config, keys)


async def init_config(uri: str,
                      db: Optional[int] = None, *,
                      default_config: Optional[str] = None,
                      keys: Optional[FrozenSet[str]] = None):
    global async_redis
    if uri:
        async_redis = await aioredis.create_redis_pool(uri, db=db)
    if default_config:
        await load_default_config(default_config, keys)


async def get_config_value(key: str, t: Type[T] = str) -> T:
    value = await async_redis.get(key, encoding='utf-8')
    if value:
        return t(str(value))
    elif key in default_configuration:
        value = default_configuration[key]
        await async_redis.set(key, t(value))
        return value


def get_config_value_sync(key: str, t: Type[T] = str) -> T:
    value = redis.get(key)
    if value:
        return t(str(value, encoding='utf-8'))
    elif key in default_configuration:
        value = default_configuration[key]
        redis.set(key, t(value))
        return value
