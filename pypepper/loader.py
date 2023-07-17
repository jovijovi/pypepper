from typing import Callable

from pypepper.errors import ERROR_INVALID_MODULE_NAME, ERROR_INVALID_LOADER, ERROR_NOT_FOUND_MODULE
from pypepper.exceptions import InternalException


class Loader:
    _module_loader_mapper = {}

    def __init__(self):
        pass

    def register(self, module_name: str, func: Callable[[], None]):
        if not module_name:
            raise InternalException(ERROR_INVALID_MODULE_NAME)

        if not func:
            raise InternalException(ERROR_INVALID_LOADER)

        if module_name in self._module_loader_mapper:
            return

        self._module_loader_mapper[module_name] = func

    def load(self, module_name: str, func: Callable[[], None] = None):
        if not module_name:
            raise InternalException(ERROR_INVALID_MODULE_NAME)

        if func:
            self.register(module_name, func)

        if module_name not in self._module_loader_mapper:
            raise InternalException(ERROR_NOT_FOUND_MODULE)

        return self._module_loader_mapper.get(module_name)()


loader = Loader()
