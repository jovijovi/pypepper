from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pypepper.errors import ERROR_INVALID_LOADER, ERROR_INVALID_MODULE_NAME, ERROR_NOT_FOUND_MODULE
from pypepper.exceptions import InternalException


class Loader:
    _instance: Loader | None = None
    _module_loader_mapper: dict[str, Callable[[], Any]]

    def __new__(cls) -> Loader:
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._module_loader_mapper = {}
            cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        pass

    def register(self, module_name: str, func: Callable[[], Any]) -> None:
        if not module_name:
            raise InternalException(ERROR_INVALID_MODULE_NAME)

        if func is None:
            raise InternalException(ERROR_INVALID_LOADER)

        if module_name in self._module_loader_mapper:
            return

        self._module_loader_mapper[module_name] = func

    def load(self, module_name: str, func: Callable[[], Any] | None = None) -> Any:
        if not module_name:
            raise InternalException(ERROR_INVALID_MODULE_NAME)

        if func is not None:
            self.register(module_name, func)

        if module_name not in self._module_loader_mapper:
            raise InternalException(ERROR_NOT_FOUND_MODULE)

        return self._module_loader_mapper[module_name]()


loader = Loader()
