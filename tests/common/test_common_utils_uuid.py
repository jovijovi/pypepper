import pytest

from pypepper.common.utils import uuid


def test_new_uuid():
    for i in range(10):
        result = uuid.new_uuid()
        print("UUID=", result)
        assert len(result) == 32 + 4


def test_new_uuid_32bits():
    for i in range(10):
        result = uuid.new_uuid_32bits()
        print("UUID=", result)
        assert len(result) == 32


def test_custom_uuid():
    for i in range(10):
        result = uuid.custom_uuid(6)
        print("UUID=", result)
        assert len(result) == 6

    try:
        print(uuid.custom_uuid(0))
    except Exception as e:
        print("Expected error=", e)


if __name__ == '__main__':
    pytest.main()
