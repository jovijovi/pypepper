import os
import signal

from pedro.common.log import log
from pedro.common.utils import time

signals = [
    signal.SIGINT,
    signal.SIGTERM,
    signal.SIGHUP,
]


def shutdown():
    log.close()
    print("[{}] ### Logger close done.".format(time.get_local_datetime()))
    os.abort()


def handler(signal_number: int, frame):
    signal_name = signal.Signals(signal_number).name
    log.info("PID={}, Signal={}({}), system exit", os.getpid(), signal_name, signal_number)
    shutdown()


def handle_signals():
    for sig in signals:
        signal.signal(sig, handler)
