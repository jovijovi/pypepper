import unittest

from pedro.common.utils import uuid


class TestCaseUUID(unittest.TestCase):
    def test_new_uuid(self):
        for i in range(3):
            result = uuid.new_uuid()
            print("UUID=", result)
            self.assertEqual(len(result), 32 + 4)

    def test_new_uuid_32bits(self):
        for i in range(3):
            result = uuid.new_uuid_32bits()
            print("UUID=", result)
            self.assertEqual(len(result), 32)

    def test_custom_uuid(self):
        for i in range(3):
            result = uuid.custom_uuid(6)
            print("UUID=", result)
            self.assertEqual(len(result), 6)

        try:
            print(uuid.custom_uuid(0))
        except Exception as e:
            print("Expected error=", e)


if __name__ == '__main__':
    unittest.main()
