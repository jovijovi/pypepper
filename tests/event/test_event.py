import pytest

from pypepper.common.security.crypto.elliptic.algorithm import HashAlgorithmName
from pypepper.common.security.crypto.elliptic.ecdsa import ecdsa
from pypepper.event import event

mock_event_id = 'e3e5866b-79ae-4cd0-8a84-31bcb5ec5b27'
mock_event_namespace = 'foo'
mock_event_version = '3'
mock_event_request_id = 'f74fb3a2-0b8d-4660-a717-d3859fb015f3'
mock_event_sender = 'Johnson'
mock_event_flow = 'EventFlowGoHome'
mock_event_name = 'OpenDoor'
mock_event_src = 'Closed'
mock_event_payload_1 = {
    "category": "test_category_1",
    "id": "5c196092-0133-461c-aa44-ea70909f9291",
    "digest": b"digest_1_bytes",
    "raw": b"raw_1_bytes"
}
mock_event_payload_2 = {
    "category": "test_category_2",
    "id": "6d5db04b-48ea-444d-bfae-5482dba3a75b",
    "digest": b"digest_2_bytes",
    "raw": b"raw_2_bytes"
}
mock_event_payload_hash_hex = '9719db8ddcd0062ead930fe1226ca4ffe9e0d2cebec148e99166e47b443689d4'


def test_new_event():
    evt1 = event.new()
    evt2 = event.new()
    evt3 = event.new()
    print("New event1=", evt1)
    print("New event2=", evt2)
    print("New event3=", evt3)
    assert evt1.data.header.id != evt2.data.header.id != evt3.data.header.id


def test_set_event_id():
    evt = event.new()
    evt.set_event_id(mock_event_id)
    print("EventID=", evt.data.header.id)
    assert evt.data.header.id == mock_event_id


def test_set_event_namespace():
    evt = event.new()
    evt.set_event_namespace(mock_event_namespace)
    print("EventNamespace=", evt.data.header.namespace)
    assert evt.data.header.namespace == mock_event_namespace


def test_set_event_version():
    evt = event.new()
    evt.set_event_version(mock_event_version)
    print("EventVersion=", evt.data.header.version)
    assert evt.data.header.version == mock_event_version


def test_set_event_request_id():
    evt = event.new()
    evt.set_request_id(mock_event_request_id)
    print("EventRequestID=", evt.data.header.request_id)
    assert evt.data.header.request_id == mock_event_request_id


def test_set_event_sender():
    evt = event.new()
    evt.set_sender(mock_event_sender)
    print("EventSender=", evt.data.header.sender)
    assert evt.data.header.sender == mock_event_sender


def test_set_flow():
    evt = event.new()
    evt.set_flow(mock_event_flow)
    print("EventFlow=", evt.data.flow)
    assert evt.data.flow == mock_event_flow


def test_set_name():
    evt = event.new()
    evt.set_name(mock_event_name)
    print("EventName=", evt.data.name)
    assert evt.data.name == mock_event_name


def test_set_src():
    evt = event.new()
    evt.set_src(mock_event_src)
    print("EventSourceState=", evt.data.src)
    assert evt.data.src == mock_event_src


def test_set_payload():
    evt = event.new()

    payload = event.Payload(mock_event_payload_1)
    payload_id = payload.id
    digest = payload.digest
    print("Payload1's ID=", payload_id)
    print("Payload1's digest=", digest)

    evt.set_payload(payload)
    print("Payload1=", evt.data.payload)
    assert evt.data.payload.id == mock_event_payload_1.get("id")

    evt.set_payload(event.Payload(mock_event_payload_2))
    print("Payload2=", evt.data.payload)
    assert evt.data.payload.id == mock_event_payload_2.get("id")


def test_add_payload():
    evt = event.new()
    evt.add_payload(
        category="test_category_3",
        payload_id="82956bfd-b367-411d-a474-a9d8f3c9dde5",
        raw=b"raw_3_bytes",
        hash_alg="SHA256",
    )

    print("PayloadID=", evt.data.payload.id)
    print("Payload's digest=", evt.data.payload.digest.hex())
    print("Payload=", evt.data.payload)

    assert evt.data.payload.id == "82956bfd-b367-411d-a474-a9d8f3c9dde5"
    assert evt.data.payload.digest.hex() == mock_event_payload_hash_hex


def test_add_invalid_payload():
    evt = event.new()

    try:
        evt.add_payload(
            payload_id='',
            category='test_category',
            raw=b"raw_bytes",
            hash_alg="SHA256",
        )
    except Exception as e:
        print("Expected error=", e)

    try:
        evt.add_payload(
            payload_id='6829a99a-60b0-4e9d-b04c-9c532a3bae40',
            category='',
            raw=b"raw_bytes",
            hash_alg="SHA256",
        )
    except Exception as e:
        print("Expected error=", e)

    try:
        evt.add_payload(
            payload_id='6829a99a-60b0-4e9d-b04c-9c532a3bae40',
            category='test_category',
            raw=bytes(),
            hash_alg="SHA256",
        )
    except Exception as e:
        print("Expected error=", e)


def test_event_sign_verify():
    evt = event.new()

    evt.set_event_namespace('namespace')
    evt.set_request_id('dd683066-e68d-4d7b-92f0-64c772403e45')
    evt.set_sender('sender')
    evt.add_payload(
        payload_id='009888ce-4fa8-4ece-9783-f13fe6bc720e',
        category='TestCategory',
        raw=b'Hello, world!',
    )
    print("Event=", evt)

    # Get private/public key (PEM)
    private_key = ecdsa.new_key_pair()
    private_key_pem = ecdsa.get_private_key_pem(private_key)
    public_key_pem = ecdsa.get_public_key_pem(private_key)

    sig = evt.sign(private_key_pem, HashAlgorithmName.SHA256)
    print("Signature=", sig.hex())

    result = evt.verify(public_key_pem, HashAlgorithmName.SHA256)
    print("Verify result=", result)

    assert result is True


if __name__ == '__main__':
    pytest.main()
