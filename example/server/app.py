import json

from flask import Flask

from pedro.common.log import log
from pedro.logo import logo

log.logo(logo)

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


if __name__ == '__main__':
    app.run()
