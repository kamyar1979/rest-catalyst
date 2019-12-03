from contextlib import contextmanager
from datetime import datetime

import pika
from typing import List, Any

from catalyst.constants import MimeTypes

from catalyst.extensions import raw_serialize

connections: List[pika.BlockingConnection] = []
serialization_format: str = MimeTypes.JSON
connection_url: str = ''
pool_size: int = 5
pool_recycle_period: int = 900
last_pool_init: datetime = datetime.utcnow()


def renew_pool():
    global last_pool_init, connections
    connections.clear()
    connections = [pika.BlockingConnection(pika.connection.URLParameters(connection_url))
                   for i in range(pool_size)]
    last_pool_init = datetime.utcnow()


@contextmanager
def acquire() -> pika.BlockingConnection:
    if (datetime.utcnow() - last_pool_init).seconds > pool_recycle_period:
        renew_pool()
    if not connections:
        renew_pool()
    con = connections.pop()
    yield con
    connections.append(con)


def publish_event(exchange_name: str, routing_key: str, data: Any):
    with acquire() as connection:
        with connection.channel() as channel:
            channel.exchange_declare(exchange_name, durable=True, exchange_type='topic')
            channel.basic_publish(exchange=exchange_name,
                                  routing_key=routing_key,
                                  body=raw_serialize(data, serialization_format),
                                  properties=pika.BasicProperties(content_type=serialization_format))
