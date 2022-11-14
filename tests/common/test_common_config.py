import json

import pytest

from pedro.common.config import config
from pedro.common.log import log


def test_load_config():
    config.load_config('./conf/app.config.yaml')
    result = config.get_yml_config()
    print("YmlConfig=", json.dumps(result, indent=4))
    log.info("Config loaded")


if __name__ == '__main__':
    pytest.main()
