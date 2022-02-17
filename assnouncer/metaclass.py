from __future__ import annotations

from typing import TypeVar

T = TypeVar("T", bound="Descriptor")


class Descriptor(type):
    def __new__(meta, name, bases, class_dict):
        cls = super(Descriptor, meta).__new__(meta, name, bases, class_dict)

        if bases:
            cls.validate()

        return cls

    def validate(cls):
        pass