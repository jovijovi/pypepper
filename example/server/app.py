import json

from flask import Flask

from pedro.common import system
from pedro.common.config import config
from pedro.common.log import log
from pedro.logo import logo

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    """A multi-line
    docstring.
    """
    return 'Hello World!'


@app.route('/health')
def health():  # put application's code here
    log.request_id().debug("health")
    return json.dumps("health")


def main():
    log.logo(logo)
    system.handle_signals()
    config.load_config()

    app.run(host='0.0.0.0', port=55550)


if __name__ == '__main__':
    main()
