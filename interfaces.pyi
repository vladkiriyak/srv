from abc import ABC, abstractmethod


class HTTPObject(ABC):

    @property
    @abstractmethod
    def protocol(self): ...

    @property
    @abstractmethod
    def headers(self): ...

    @property
    @abstractmethod
    def raw(self) -> bytes: ...
