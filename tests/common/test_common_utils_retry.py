import pytest

from pypepper.common.utils import retry


def transistor(in_voltage: int) -> int:
    voltage = 1
    delta = in_voltage - voltage
    if delta > 0:
        raise Exception("too high")
    elif delta < 0:
        raise Exception("too low")

    return in_voltage


def hello_world() -> None:
    print("Hello, world!")


def answer(arg: int = 42) -> int:
    return arg


def test_retry_simple():
    retry.run(func=hello_world)


def test_retry_with_default_params():
    result = retry.run(func=answer, retry_times=3, retry_interval=5, verbose_log=False)
    print(f"The Answer is {result}, Type={type(result)}")
    assert isinstance(result, int)
    assert result == 42


def test_retry_lambda():
    def say(words: str) -> str:
        return words

    result1 = retry.run(func=lambda: say("hi"), retry_times=3, retry_interval=1)
    print(f'Say "{result1}"')

    result2 = retry.run(func=lambda words='hi': say(words), retry_times=3, retry_interval=1)
    print(f'Say "{result2}"')

    result3 = retry.run(func=lambda: answer(0), retry_times=3, retry_interval=1)
    print(f'The Answer is "{result3}"')


def test_transistor():
    try:
        result = retry.run(func=lambda: transistor(0))
        print("Result=", result)
    except Exception as e:
        print("Expected error=", e)

    try:
        result = retry.run(
            func=lambda: transistor(2),
            retry_times=2,
            retry_interval=retry.random_retry_interval(),
            verbose_log=False,
        )
        print("Result=", result)
    except Exception as e:
        print("Expected error=", e)

    try:
        result = retry.run(func=lambda: transistor(42))
        print("Result=", result)
        assert result == 42
    except Exception as e:
        print(e)


def test_invalid_func():
    try:
        retry.run(None)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    pytest.main()
