import unittest

from pedro.common.utils import time


class TestCaseTime(unittest.TestCase):
    def test_get_local_datetime(self):
        result = time.get_local_datetime()
        print("LocalDateTime=", result)

    def test_get_utc_datetime(self):
        result = time.get_utc_datetime()
        print("UTCDateTime=", result)


if __name__ == '__main__':
    unittest.main()
