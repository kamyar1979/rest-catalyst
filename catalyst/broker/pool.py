from contextlib import contextmanager

import pika
from typing import List, Any

from catalyst.constants import MimeTypes

from catalyst.extensions import raw_serialize

connections: List[pika.BlockingConnection] = []
serialization_format: str = MimeTypes.JSON


@contextmanager
def acquire() -> pika.BlockingConnection:
    con = connections.pop()
    yield con
    connections.append(con)


def publish_event(exchange_name: str, routing_key: str, data: Any):
    with acquire() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange_name, durable=True, exchange_type='topic')
        channel.basic_publish(exchange=exchange_name,
                              routing_key=routing_key,
                              body=raw_serialize(data, serialization_format),
                              properties=pika.BasicProperties(content_type=serialization_format))

