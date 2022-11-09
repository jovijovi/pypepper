from abc import abstractmethod, ABCMeta

from flask import Flask


class ITaskHandler(metaclass=ABCMeta):
    @abstractmethod
    def register_handlers(self, app: Flask):
        pass

    @abstractmethod
    def use_middleware(self, app: Flask):
        pass
