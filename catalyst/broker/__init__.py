from typing import Optional

import pika

from . import pool

connection_url: str = ''
pool_size: int = 10


def register_broker(url: str, pool_size: int = 10, format: Optional[str] = None):
    if format:
        pool.serialization_format = format
    connection_url = url
    pool_size = pool_size
    pool.connections = [pika.BlockingConnection(pika.connection.URLParameters(connection_url))
                        for i in range(pool_size)]