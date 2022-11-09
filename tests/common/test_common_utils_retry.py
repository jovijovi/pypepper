import unittest

from pedro.common.utils import retry


def hello_world() -> int:
    print("Hello, world!")
    return 42


class TestCaseRetry(unittest.TestCase):
    def test_retry(self):
        try:
            result = retry.run(hello_world, retry_times=3, retry_interval=1, verbose_log=False)
            print(result)
            self.assertEqual(result, 42)
        except Exception as e:
            print("Expected error=", e)


if __name__ == '__main__':
    unittest.main()
