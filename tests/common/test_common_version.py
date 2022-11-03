import unittest

from pedro.common.version import version


class TestCaseVersion(unittest.TestCase):
    def test_get_version_info(self):
        ver = version.get_version_info()
        print("Version=", ver)
        self.assertNotEqual(ver, None)


if __name__ == '__main__':
    unittest.main()
