import signal
import unittest

from pedro.common import system


class TestCaseSys(unittest.TestCase):
    def test_something(self):
        system.handle_signals()
        signal.raise_signal(signal.SIGINT)


if __name__ == '__main__':
    unittest.main()
