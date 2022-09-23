from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Generic, Iterator, TypeVar
from threading import RLock

T = TypeVar("T")


@dataclass(frozen=True)
class Queue(Generic[T]):
    data: deque[T] = field(default_factory=deque)
    lock: RLock = field(default_factory=RLock)

    def empty(self) -> bool:
        return self.peek() is None

    def peek(self) -> T:
        with self.lock:
            if not self.data:
                return None

            return self.data[0]

    def pop(self) -> T:
        with self.lock:
            if not self.data:
                return None

            return self.data.popleft()

    def put(self, item: T):
        assert item is not None

        with self.lock:
            self.data.append(item)

    def clear(self):
        with self.lock:
            self.data.clear()

    def __iter__(self) -> Iterator[T]:
        with self.lock:
            yield from self.data
