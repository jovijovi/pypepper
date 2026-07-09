from abc import ABCMeta


class ITag(metaclass=ABCMeta):
    key: str
    value: str


class Tag(ITag):
    def __init__(self, key: str = "", value: str = ""):
        self.key = key
        self.value = value
