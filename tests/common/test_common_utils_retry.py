import pytest

from pypepper.common.utils import retry
from pypepper.exceptions import InternalException


def transistor(in_voltage: int) -> int:
    voltage = 1
    delta = in_voltage - voltage
    if delta > 0:
        raise Exception("too high")
    elif delta < 0:
        raise Exception("too low")
    return in_voltage


def hello_world() -> str:
    return "Hello, world!"


def answer(arg: int = 42) -> int:
    return arg


def test_retry_simple():
    assert retry.run(func=hello_world, retry_times=1, retry_interval=0) == "Hello, world!"


def test_retry_with_default_params():
    result = retry.run(func=answer, retry_times=3, retry_interval=0, verbose_log=False)
    assert isinstance(result, int)
    assert result == 42


def test_retry_lambda():
    def say(words: str) -> str:
        return words

    assert retry.run(func=lambda: say("hi"), retry_times=1, retry_interval=0) == "hi"
    assert retry.run(func=lambda: answer(0), retry_times=1, retry_interval=0) == 0


def test_transistor():
    with pytest.raises(InternalException):
        retry.run(func=lambda: transistor(0), retry_times=2, retry_interval=0, verbose_log=False)

    with pytest.raises(InternalException):
        retry.run(
            func=lambda: transistor(2),
            retry_times=2,
            retry_interval=0,
            verbose_log=False,
        )

    assert retry.run(func=lambda: transistor(1), retry_times=1, retry_interval=0) == 1


def test_invalid_func():
    with pytest.raises(InternalException, match='invalid function'):
        retry.run(None)


def test_invalid_params():
    with pytest.raises(InternalException, match='invalid retry times'):
        retry.run(func=hello_world, retry_times=0)

    with pytest.raises(InternalException, match='invalid retry interval'):
        retry.run(func=hello_world, retry_interval=-1)
