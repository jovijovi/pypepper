"""HTTP task handler and middleware interfaces."""

from abc import ABCMeta, abstractmethod

from fastapi import FastAPI


class ITaskHandler(metaclass=ABCMeta):
    @abstractmethod
    def register_handlers(self, app: FastAPI) -> None:
        pass

    @abstractmethod
    def use_middleware(self, app: FastAPI) -> None:
        pass
