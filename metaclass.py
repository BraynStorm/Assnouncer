from __future__ import annotations

from typing import TypeVar, List

T = TypeVar("T")


class Descriptor(type):
    def __new__(meta, name, bases, class_dict):
        cls = super(Descriptor, meta).__new__(meta, name, bases, class_dict)

        def init(*_, **__):
            del _, __
            raise RuntimeError("Should not instantiate this")

        setattr(cls, "__init__", init)

        if bases:
            cls.validate()

        return cls

    @classmethod
    def validate(cls):
        pass

    def get_instances(cls: T) -> List[T]:
        subclasses = []

        queue = [cls]
        while queue:
            current_class = queue.pop()
            for child in current_class.__subclasses__():
                if child not in subclasses:
                    subclasses.append(child)
                    queue.append(child)

        return subclasses
