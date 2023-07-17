from __future__ import annotations

from abc import ABCMeta, abstractmethod


class IHeader(metaclass=ABCMeta):
    """
    Event header interface
    """

    __slots__ = ["id", "namespace", "timestamp", "version", "request_id", "sender"]

    # Event ID
    id: str

    # Event namespace
    namespace: str

    # Event timestamp(RFC3339)
    timestamp: str

    # Event version
    version: str

    # Request ID
    request_id: str | None

    # Sender name
    sender: str


class IPayload(metaclass=ABCMeta):
    """
    Event payload interface
    """

    __slots__ = ["id", "category", "digest", "raw"]

    # Payload ID
    id: str

    # Payload category
    category: str

    # Raw data digest
    digest: bytes | None

    # Raw
    raw: bytes | None


class IData(metaclass=ABCMeta):
    """
    Event data interface
    """

    __slots__ = ["header", "flow", "name", "src", "payload"]

    # Event header
    header: IHeader

    # Event flow name
    flow: str

    # Event name
    name: str

    # Event source state
    src: str

    # Event payload
    payload: IPayload


class IEvent(metaclass=ABCMeta):
    """
    Event interface
    """

    __slots__ = ["signature", "data"]

    # Signature (optional)
    signature: bytes | None

    # Event data
    data: IData

    @abstractmethod
    def set_event_id(self, event_id: str):
        """
        Set event ID.
        :param event_id: event ID.
        :return: None.
        """
        pass

    @abstractmethod
    def set_event_namespace(self, namespace: str):
        """
        Set event namespace.
        :param namespace: namespace.
        :return: None.
        """
        pass

    @abstractmethod
    def set_event_version(self, version: str):
        """
        Set event version.
        :param version: event version.
        :return: None.
        """
        pass

    @abstractmethod
    def set_request_id(self, req_id: str):
        """
        Set event request ID.
        :param req_id: event request ID.
        :return: None.
        """
        pass

    @abstractmethod
    def set_sender(self, sender: str):
        """
        Set event sender.
        :param sender: event sender.
        :return: None.
        """
        pass

    @abstractmethod
    def set_flow(self, flow: str):
        """
        Set event flow.
        :param flow: event flow.
        :return: None.
        """
        pass

    @abstractmethod
    def set_name(self, name: str):
        """
        Set event name.
        :param name: event name.
        :return: None.
        """
        pass

    @abstractmethod
    def set_src(self, src: str):
        """
        Set event original state
        :param src: event original state
        :return: None
        """
        pass

    @abstractmethod
    def set_payload(self, payload: IPayload):
        """
        Set event payload.
        :param payload: event payload.
        :return: None..
        """
        pass

    @abstractmethod
    def add_payload(self, payload_id: str, category: str, raw: bytes, hash_alg: str | None):
        """
        Add event payload
        :param payload_id: payload ID
        :param category: payload category
        :param raw: raw data
        :param hash_alg: hash algorithm
        :return: None
        """
        pass

    @abstractmethod
    def sign(self, certificate: str, hash_alg: str) -> bytes:
        """
        Sign event
        :param certificate: private key (PEM)
        :param hash_alg: hash algorithm
        :return: signature
        """
        pass

    @abstractmethod
    def verify(self, certificate: str, hash_alg: str) -> bool:
        """
        Verify event signature
        :param certificate: public key (PEM)
        :param hash_alg: hash algorithm
        :return: Valid / Invalid signature
        """
        pass

    @abstractmethod
    def marshal(self) -> str:
        """
        Marshal event to JSON string.
        :return: JSON string.
        """
        pass
