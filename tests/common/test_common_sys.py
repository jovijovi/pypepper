import signal

from pypepper.common import system


def test_handle_signals_registers_handlers():
    system.handle_signals()
    assert signal.getsignal(signal.SIGINT) is system.handler
    assert signal.getsignal(signal.SIGTERM) is system.handler
