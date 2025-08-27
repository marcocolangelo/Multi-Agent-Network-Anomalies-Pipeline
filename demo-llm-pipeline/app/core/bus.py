import asyncio, collections
from typing import Callable, Awaitable
from .messages import Msg

class EventBus:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.subscribers: dict[str, list[Callable[[Msg], Awaitable]]] = collections.defaultdict(list)

    async def publish(self, msg: Msg):
        await self.queue.put(msg)

    def subscribe(self, role: str, coro: Callable[[Msg], Awaitable]):
        self.subscribers[role].append(coro)

    async def start(self):
        while True:
            msg: Msg = await self.queue.get()
            for coro in self.subscribers.get(msg.role, []):
                asyncio.create_task(coro(msg))
