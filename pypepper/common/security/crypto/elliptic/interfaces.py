from abc import ABCMeta, abstractmethod

from cryptography.hazmat.primitives.asymmetric import ec


class IElliptic(metaclass=ABCMeta):
    @abstractmethod
    def new_key_pair(self) -> ec.EllipticCurvePrivateKey: ...

    @abstractmethod
    def sign(self, data: bytes, certificate: bytes, hash_alg: str, passphrase: bytes | None = None) -> bytes: ...

    @abstractmethod
    def verify(self, data: bytes, certificate: bytes, sig: bytes, hash_alg: str) -> bool: ...
