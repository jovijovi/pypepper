from pedro.common import system
from pedro.common.config import config
from pedro.common.log import log
from pedro.logo import logo
from pedro.network.http import server


def main():
    log.logo(logo)
    system.handle_signals()
    config.load_config()

    server.run()


if __name__ == '__main__':
    main()
