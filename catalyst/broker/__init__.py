from typing import Optional

import pika

from . import pool


def register_broker(url: str, pool_size: int = 10, format: Optional[str] = None):
    if format:
        pool.serialization_format = format
    pool.connection_url = url
    pool.pool_size = pool_size
    pool.connections = [pika.BlockingConnection(pika.connection.URLParameters(url))
                        for i in range(pool_size)]
