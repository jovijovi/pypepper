from __future__ import annotations

import os
import signal
import types

from pypepper.common.log import log
from pypepper.common.utils import time

signals = [
    signal.SIGINT,
    signal.SIGTERM,
    signal.SIGHUP,
]


def shutdown() -> None:
    """
    Shutdown the program
    :return: None
    """

    from pypepper.common.tracing import shutdown as tracing_shutdown

    tracing_shutdown()
    log.close()
    print(f"[{time.get_local_datetime()}] ### Logger close done.")
    os.abort()


def handler(signal_number: int, frame: types.FrameType | None) -> None:
    """
    The function handler for signal number.
    :param signal_number: signal number.
    :param frame: the current stack frame.
    :return: None.
    """

    signal_name = signal.Signals(signal_number).name
    log.info("PID={}, Signal={}({}), Frame={}, system exit", os.getpid(), signal_name, signal_number, frame)
    shutdown()


def handle_signals() -> None:
    """
    Handle the signals
    :return: None
    """

    for sig in signals:
        signal.signal(sig, handler)
