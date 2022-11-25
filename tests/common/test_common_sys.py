import pytest

from pypedro.common import system


def test_handle_signals():
    system.handle_signals()
    # signal.raise_signal(signal.SIGINT)


if __name__ == '__main__':
    pytest.main()
