from datetime import datetime
from typing import Optional

import pika

from . import pool


def register_broker(url: str,
                    pool_size: int = 10,
                    format: Optional[str] = None,
                    pool_recycle_period: Optional[int] = None):
    if format:
        pool.serialization_format = format
    pool.connection_url = url
    pool.pool_size = pool_size
    pool.pool_recycle_period = pool_recycle_period
    pool.renew_pool()
