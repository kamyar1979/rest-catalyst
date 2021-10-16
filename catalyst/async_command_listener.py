import inspect
import logging
from typing import Type

import pynng
import umsgpack


async def listen_for_topic(self):
    with pynng.Sub0() as sock:
        sock.subscribe(self.topic.encode('utf-8'))
        sock.dial(self.address, block=True)
        logging.info('Logging configuration listener for topic %s started.', self.topic)

        while True:
            message = await sock.arecv_msg()
            _, command, blob = message.bytes.split(b' ', 3)
            data = umsgpack.loads(blob)
            cmd = command.decode('utf-8')
            if cmd in self.handlers:
                await self.handlers[cmd](data)


def command_handler(func):
    sig = inspect.signature(func)
    func_args = sig.parameters
    param_names = tuple(func_args.keys())

    async def wrapper(data):
        await func(**{k: data.get(k) for k in param_names})

    wrapper.__name__ = func.__name__
    wrapper.__signature__ = sig

    return wrapper


def register_command_handler(cls: Type):
    def constructor(self, address: str, topic: str):
        self.address = address
        self.topic = topic
        self.handlers = {}
        for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name != '__init__':
                self.handlers[name] = command_handler(getattr(self, name))
        cls.listen = listen_for_topic

    cls.__init__ = constructor
    return cls
