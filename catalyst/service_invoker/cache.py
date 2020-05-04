from typing import TypeVar, Generic, Type

T = TypeVar('T')

async def get_cache_item(key: str, t: Type[T]) -> Generic[T]:
    pass


async def set_cache_item(key: str, obj: T):
    pass


async def get_cache_item_sync(key: str, t: Type[T]) -> Generic[T]:
    pass


async def set_cache_item_sync(key: str, obj: T):
    pass