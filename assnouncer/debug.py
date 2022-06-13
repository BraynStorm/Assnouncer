from __future__ import annotations
from collections import defaultdict

import numpy as np
import time
import datetime

from dataclasses import dataclass
from typing import Callable, ClassVar, List, Tuple, TypeVar

T = TypeVar("T")
U = TypeVar("U")


PROFILE_DATA: defaultdict[Callable, List[ProfileEntry]] = defaultdict(list)

ENABLE_DEBUGGING = False


@dataclass
class Timer:
    start: float = 0
    stop: float = 0
    deduction: float = 0

    ACTIVE_TIMERS: ClassVar[List[Timer]] = []

    def deduct(self, amount: float):
        self.deduction += amount

    def total_time(self) -> float:
        return self.stop - self.start

    def active_time(self) -> float:
        return self.total_time() - self.deduction

    def __enter__(self) -> Timer:
        Timer.ACTIVE_TIMERS.append(self)

        self.deduction = 0
        self.start = time.perf_counter()

        return self

    def __exit__(self, *_):
        self.stop = time.perf_counter()

        Timer.ACTIVE_TIMERS.pop()
        if Timer.ACTIVE_TIMERS:
            Timer.ACTIVE_TIMERS[-1].deduct(self.total_time())


@dataclass(slots=True)
class ProfileEntry:
    total_time: float
    active_time: float


if ENABLE_DEBUGGING:
    def print_report(reset: bool = True):
        def format_time(time: float) -> str:
            return str(datetime.timedelta(seconds=time))

        def get_times(data: np.ndarray) -> Tuple[str, str, str]:
            min = data.min()
            max = data.max()
            mean = data.mean()
            min, max, mean = map(format_time, (min, max, mean))
            return min, max, mean

        parts = ["[debug] Profiling report:"]
        for func, entries in PROFILE_DATA.items():
            data = np.array([(entry.total_time, entry.active_time) for entry in entries])
            total_time = data[:, 0]
            active_time = data[:, 1]
            total = get_times(total_time)
            active = get_times(active_time)
            parts.extend([
                f"[debug]   Function: {func.__qualname__}",
                f"[debug]     Count:    {len(entries)}",
                f"[debug]     Min:      {total[0]} ({active[0]})",
                f"[debug]     Max:      {total[1]} ({active[1]})",
                f"[debug]     Mean:     {total[2]} ({active[2]})"
            ])

            if reset:
                entries.clear()
        print("\n".join(parts))

    def profiled(func: Callable) -> Callable:
        data = PROFILE_DATA[func]

        def wrapper(*args, **kwargs):
            with Timer():
                with Timer() as timer:
                    result = func(*args, **kwargs)

                with Timer():
                    entry = ProfileEntry(
                        total_time=timer.total_time(),
                        active_time=timer.active_time()
                    )
                    data.append(entry)

                    return result

        return wrapper
else:
    def print_report(reset: bool = True):
        pass

    def profiled(func: Callable) -> Callable:
        return func
