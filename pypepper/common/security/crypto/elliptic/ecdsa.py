from cryptography import exceptions
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from pypepper.common.security.crypto.elliptic import algorithm
from pypepper.common.security.crypto.elliptic.interfaces import IElliptic


class ECDSA(IElliptic):
    def new_key_pair(self) -> ec.EllipticCurvePrivateKey:
        return ec.generate_private_key(
            ec.SECP256K1()
        )

    def sign(self, data: bytes, certificate: bytes, hash_alg: str, passphrase: bytes = None):
        private_key: ec.EllipticCurvePrivateKey = serialization.load_pem_private_key(certificate, passphrase)

        return private_key.sign(
            data=data,
            signature_algorithm=ec.ECDSA(algorithm.get_hash_algorithm(hash_alg))
        )

    def verify(self, data: bytes, certificate: bytes, sig: bytes, hash_alg: str) -> bool:
        public_key: ec.EllipticCurvePublicKey = serialization.load_pem_public_key(certificate)

        try:
            public_key.verify(
                signature=sig,
                data=data,
                signature_algorithm=ec.ECDSA(algorithm.get_hash_algorithm(hash_alg)))
        except exceptions.InvalidSignature:
            return False

        return True

    @staticmethod
    def get_private_key_pem(private_key: ec.EllipticCurvePrivateKey, passphrase: bytes = None) -> bytes:
        if passphrase:
            encryption_alg = serialization.BestAvailableEncryption(passphrase)
        else:
            encryption_alg = serialization.NoEncryption()
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_alg
        )

    @staticmethod
    def get_public_key_pem(private_key: ec.EllipticCurvePrivateKey) -> bytes:
        return private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


ecdsa = ECDSA()
