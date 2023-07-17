import pytest

from pypepper.common.utils.random import random


def test_rand_int_between():
    for i in range(10):
        result = random.rand_int_between(-3, 3)
        print("rand_int_between(-3, 3)=", result)
        assert result != 3


def test_rand_uint_between():
    for i in range(10):
        result = random.rand_uint_between(0, 3)
        print("rand_uint_between(0, 3)=", result)
        assert result != 3

    try:
        print(random.rand_uint_between(-1, 1))
    except Exception as e:
        print("Expected error=", e)


def test_rand_boolean():
    for i in range(10):
        result = random.rand_boolean()
        print("rand_boolean()=", result)
        assert result in [True, False]


def test_rand_case():
    for i in range(10):
        result = random.rand_case('a0b1c2d3e4f5. TEST"测试')
        print(result)


def test_rand_uppercase():
    for i in range(10):
        result = random.rand_uppercase('a0b1c2d3e4f5. тест"テスト')
        print(result)


def test_rand_lowercase():
    for i in range(10):
        result = random.rand_lowercase('A0B1C2D3E4F5. Ensayo"테스트')
        print(result)


def test_rand_int_seed():
    for i in range(10):
        result = random.rand_int_seed(4)
        print("rand_int_seed()=", result)
        assert result < 10000


def test_rand_hex_seed():
    for i in range(10):
        result = random.rand_hex_seed()
        print("rand_str_seed()=", result)
        assert len(result) == random.DEFAULT_ENTROPY * 2


if __name__ == '__main__':
    pytest.main()
