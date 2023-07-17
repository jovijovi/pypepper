from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hashes import HashAlgorithm

from pypepper.errors import ERROR_INVALID_ALGORITHM
from pypepper.exceptions import InternalException


class HashAlgorithmName:
    """
    Hash algorithm name
    """

    MD5 = "md5"
    SHA1 = "sha1"
    SHA224 = "sha224"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"


hash_algorithms = {
    HashAlgorithmName.MD5: hashes.MD5(),
    HashAlgorithmName.SHA1: hashes.SHA1(),
    HashAlgorithmName.SHA224: hashes.SHA224(),
    HashAlgorithmName.SHA256: hashes.SHA256(),
    HashAlgorithmName.SHA384: hashes.SHA384(),
    HashAlgorithmName.SHA512: hashes.SHA512(),
}


def get_hash_algorithm(alg_: str) -> HashAlgorithm:
    alg = alg_.lower()
    if alg not in hash_algorithms:
        raise InternalException(ERROR_INVALID_ALGORITHM)
    return hash_algorithms.get(alg)
