import unittest

from pedro.common.utils.random import random


class MyTestCase(unittest.TestCase):
    def test_rand_int_between(self):
        for i in range(10):
            result = random.rand_int_between(-3, 3)
            print("rand_int_between(-3, 3)=", result)
            self.assertNotEqual(result, 3)

    def test_rand_uint_between(self):
        for i in range(10):
            result = random.rand_uint_between(0, 3)
            print("rand_uint_between(0, 3)=", result)
            self.assertNotEqual(result, 3)

        try:
            print(random.rand_uint_between(-1, 1))
        except Exception as e:
            print("Expected error=", e)

    def test_rand_boolean(self):
        for i in range(10):
            result = random.rand_boolean()
            print("rand_boolean()=", result)
            self.assertIn(result, [True, False])

    @staticmethod
    def test_rand_case():
        for i in range(10):
            result = random.rand_case('a0b1c2d3e4f5. TEST"测试')
            print(result)

    @staticmethod
    def test_rand_uppercase():
        for i in range(10):
            result = random.rand_uppercase('a0b1c2d3e4f5. тест"テスト')
            print(result)

    @staticmethod
    def test_rand_lowercase():
        for i in range(10):
            result = random.rand_lowercase('A0B1C2D3E4F5. Ensayo"테스트')
            print(result)

    def test_rand_int_seed(self):
        for i in range(10):
            result = random.rand_int_seed(4)
            print("rand_int_seed()=", result)
            self.assertLess(result, 10000)

    def test_rand_hex_seed(self):
        for i in range(10):
            result = random.rand_hex_seed()
            print("rand_str_seed()=", result)
            self.assertEqual(len(result), random.DEFAULT_ENTROPY * 2)


if __name__ == '__main__':
    unittest.main()
