import math
import secrets

from pypepper.exceptions import InternalException


class Random:
    """
    Toolkit for generating random values.
    """

    DEFAULT_ENTROPY = 64

    def __init__(self):
        self._random = secrets.SystemRandom()

    def rand_int_between(self, min_: int, max_: int) -> int:
        """
        Generate random integer in range [min_, max_)
        :param min_: min int
        :param max_: max int
        :return: random integer in range [min_, max_)
        """

        return self._random.randrange(min_, max_)

    def rand_uint_between(self, min_: int, max_: int) -> int:
        """
        Generate random uint in range [min_, max_)
        :param min_: min uint
        :param max_: max uint
        :return: random uint in range [min_, max_)
        """

        if min_ < 0 or max_ < 0:
            raise InternalException("invalid range")

        return self._random.randrange(min_, max_)

    @staticmethod
    def rand_boolean() -> bool:
        """
        Generate random boolean, range: [true, false]
        :return: random boolean in range [true, false]
        """

        return secrets.randbits(1) == 1

    def rand_case(self, inputs: str) -> str:
        """
        Generate a string of random uppercase and lowercase letters.
        :param inputs: a string.
        :return: A string of random uppercase and lowercase letters.
        """

        outputs = ""

        for c in inputs:
            if self.rand_boolean():
                outputs += c.upper()
            else:
                outputs += c.lower()

        return outputs

    def rand_uppercase(self, inputs: str) -> str:
        """
        Generate a string of random uppercase letters.
        :param inputs: a string.
        :return: A string of random uppercase letters.
        """

        outputs = ""

        for c in inputs:
            if self.rand_boolean():
                outputs += c.upper()
            else:
                outputs += c

        return outputs

    def rand_lowercase(self, inputs: str) -> str:
        """
        Generate a string of random lowercase letters.
        :param inputs: a string.
        :return: A string of random lowercase letters.
        """

        outputs = ""

        for c in inputs:
            if self.rand_boolean():
                outputs += c.lower()
            else:
                outputs += c

        return outputs

    @staticmethod
    def rand_int_seed(k: int) -> int:
        """
        Generate a random integer based on the maximum number of integer digits
        :param k: maximum number of integer digits
        :return: a random integer
        """

        bits = int(math.pow(10, k - 1)).bit_length() + 1
        return secrets.randbits(bits)

    def rand_hex_seed(self):
        """
        Generate a random string based on the DEFAULT_ENTROPY
        :return: a random string in hex.
        """

        return secrets.token_hex(self.DEFAULT_ENTROPY)


random = Random()
