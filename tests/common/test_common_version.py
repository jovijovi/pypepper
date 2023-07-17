import pytest

from pypepper.common.version import version


def test_get_version_info():
    ver = version.get_version_info()
    print("Version=", ver)
    assert ver is not None


if __name__ == '__main__':
    pytest.main()
