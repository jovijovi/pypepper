import json

import pytest

from pedro.common.config import config


def test_load_config():
    config.load_config('./conf/app.config.yaml')
    result = config.get_yml_config()
    print("YmlConfig=", json.dumps(result, indent=4))


if __name__ == '__main__':
    pytest.main()
