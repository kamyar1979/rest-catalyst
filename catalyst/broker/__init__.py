from typing import Optional

from . import pool


def register_broker(url: str,
                    pool_size: int = 10,
                    format: Optional[str] = None,
                    pool_recycle_period: Optional[int] = None):
    pool.connection_url = url
    if format:
        pool.serialization_format = format
    if pool_size:
        pool.pool_size = pool_size
    if pool_recycle_period:
        pool.pool_recycle_period = pool_recycle_period
    pool.renew_pool()
