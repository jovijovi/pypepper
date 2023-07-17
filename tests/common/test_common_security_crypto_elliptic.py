import pytest
from cryptography.hazmat.primitives import serialization

from pypepper.common.security.crypto.elliptic.algorithm import HashAlgorithmName
from pypepper.common.security.crypto.elliptic.ecdsa import ecdsa

data = b"Hello, world!"


def test_ecdsa_sign_verify():
    # New key pair
    key = ecdsa.new_key_pair()

    # Load private key
    private_key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(b"Hello")
    )
    print("## [ECDSA] private_key_pem=", private_key_pem)

    # Sign
    sig = ecdsa.sign(data, private_key_pem, HashAlgorithmName.SHA256, b"Hello")
    print("## [ECDSA] sig(hex)=", sig.hex())

    # Load public key
    public_key_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    print("## [ECDSA] public_key_pem=", public_key_pem)

    # Verify
    result = ecdsa.verify(
        data=data,
        certificate=public_key_pem,
        sig=sig,
        hash_alg='SHA256',
    )

    assert result is True


if __name__ == '__main__':
    pytest.main()
