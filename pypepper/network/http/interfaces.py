from abc import abstractmethod, ABCMeta

from fastapi import FastAPI


class ITaskHandler(metaclass=ABCMeta):
    @abstractmethod
    def register_handlers(self, app: FastAPI):
        pass

    @abstractmethod
    def use_middleware(self, app: FastAPI):
        pass
