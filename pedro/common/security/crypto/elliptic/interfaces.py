from abc import abstractmethod, ABCMeta


class IElliptic(metaclass=ABCMeta):
    @abstractmethod
    def new_key_pair(self): ...

    @abstractmethod
    def sign(self, data: bytes, certificate: bytes, hash_alg: str, passphrase: bytes = None): ...

    @abstractmethod
    def verify(self, data: bytes, certificate: bytes, sig: bytes, hash_alg: str): ...
