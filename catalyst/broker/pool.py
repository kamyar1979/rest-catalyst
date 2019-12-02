from contextlib import contextmanager

import pika
from typing import List, Any

from catalyst.constants import MimeTypes

from catalyst.extensions import raw_serialize

connections: List[pika.BlockingConnection] = []
serialization_format: str = MimeTypes.JSON
connection_url: str = ''
pool_size: int = 1

@contextmanager
def acquire() -> pika.BlockingConnection:
    con = connections.pop()
    if con.is_closed:
        con = pika.BlockingConnection(pika.connection.URLParameters(connection_url))
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

