import pytest

from pypepper.errors import (
    ERROR_INVALID_LOADER,
    ERROR_INVALID_MODULE_NAME,
    ERROR_NOT_FOUND_MODULE,
)
from pypepper.exceptions import InternalException
from pypepper.loader import Loader, loader


def foo_loader():
    return 'foo'


def bar_loader():
    return 'bar'


def test_load():
    assert loader.load('foo', foo_loader) == 'foo'
    # Re-register same name is ignored
    loader.register('foo', bar_loader)
    assert loader.load('foo') == 'foo'
    assert loader.load('bar', bar_loader) == 'bar'


def test_invalid_module_name():
    with pytest.raises(InternalException) as exc:
        loader.register('', bar_loader)
    assert str(exc.value) == ERROR_INVALID_MODULE_NAME

    with pytest.raises(InternalException):
        loader.load('')

    with pytest.raises(InternalException):
        loader.load(None)


def test_invalid_loader():
    with pytest.raises(InternalException) as exc:
        loader.register('bar_invalid', None)
    assert str(exc.value) == ERROR_INVALID_LOADER


def test_load_not_existed_module():
    with pytest.raises(InternalException) as exc:
        loader.load('not_existed_module')
    assert str(exc.value) == ERROR_NOT_FOUND_MODULE


def test_loader_is_singleton():
    assert Loader() is loader
