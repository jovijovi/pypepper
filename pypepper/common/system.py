import os
import signal

from pypepper.common.log import log
from pypepper.common.utils import time

signals = [
    signal.SIGINT,
    signal.SIGTERM,
    signal.SIGHUP,
]


def shutdown():
    """
    Shutdown the program
    :return: None
    """

    log.close()
    print("[{}] ### Logger close done.".format(time.get_local_datetime()))
    os.abort()


def handler(signal_number: int, frame):
    """
    The function handler for signal number.
    :param signal_number: signal number.
    :param frame: the current stack frame.
    :return: None.
    """

    signal_name = signal.Signals(signal_number).name
    log.info("PID={}, Signal={}({}), Frame={}, system exit", os.getpid(), signal_name, signal_number, frame)
    shutdown()


def handle_signals():
    """
    Handle the signals
    :return: None
    """

    for sig in signals:
        signal.signal(sig, handler)
