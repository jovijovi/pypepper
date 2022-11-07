import json
import unittest

from pedro.common.config import config


class TestCaseConfig(unittest.TestCase):
    def test_load_config(self):
        config.load_config('./conf/app.config.yaml')
        result = config.get_yml_config()
        print("YmlConfig=", json.dumps(result, indent=4))


if __name__ == '__main__':
    unittest.main()
