from cryptography import exceptions
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import HashAlgorithm

from pedro.common.security.crypto.elliptic.interfaces import IElliptic


class ECDSA(IElliptic):
    def new_key_pair(self) -> ec.EllipticCurvePrivateKey:
        return ec.generate_private_key(
            ec.SECP256K1()
        )

    def sign(self, data: bytes, certificate: bytes, hash_alg: HashAlgorithm, passphrase: bytes = None):
        private_key: ec.EllipticCurvePrivateKey = serialization.load_pem_private_key(certificate, passphrase)

        return private_key.sign(
            data=data,
            signature_algorithm=ec.ECDSA(hash_alg)
        )

    def verify(self, data: bytes, certificate: bytes, sig: bytes, hash_alg: HashAlgorithm) -> bool:
        public_key: ec.EllipticCurvePublicKey = serialization.load_pem_public_key(certificate)

        try:
            public_key.verify(
                signature=sig,
                data=data,
                signature_algorithm=ec.ECDSA(hash_alg))
        except exceptions.InvalidSignature:
            return False

        return True


ecdsa = ECDSA()
