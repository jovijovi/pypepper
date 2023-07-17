import pytest

from pypepper.loader import loader


def foo_loader():
    print("Foo is running...")


def bar_loader():
    print("Bar is running...")


def test_load():
    loader.register('foo', foo_loader)
    loader.register('foo', foo_loader)
    loader.load('foo')
    loader.load('foo')

    loader.load('bar', bar_loader)


def test_invalid_module_name():
    try:
        loader.register('', bar_loader)
    except Exception as e:
        print("Excepted error=", e)

    try:
        loader.load('')
    except Exception as e:
        print("Excepted error=", e)

    try:
        loader.load(None)
    except Exception as e:
        print("Excepted error=", e)


def test_invalid_loader():
    try:
        loader.register('bar', None)
    except Exception as e:
        print("Excepted error=", e)


def test_load_not_existed_module():
    try:
        loader.load('not_existed_module')
    except Exception as e:
        print("Excepted error=", e)


if __name__ == '__main__':
    pytest.main()
