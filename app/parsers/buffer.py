import struct
from dataclasses import dataclass


class ParseError(ValueError):
    pass


class ByteReader:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self._index = 0

    @property
    def remaining(self) -> int:
        return len(self._data) - self._index

    @property
    def at_end(self) -> bool:
        return self._index >= len(self._data)

    def read_fixed(self, count: int) -> bytes:
        if self.remaining < count:
            raise ParseError("Insufficient data.")
        chunk = self._data[self._index : self._index + count]
        self._index += count
        return chunk

    def read_u8(self) -> int:
        return self.read_fixed(1)[0]

    def read_u32_be(self) -> int:
        return struct.unpack(">I", self.read_fixed(4))[0]

    def read_u64_be(self) -> int:
        return struct.unpack(">Q", self.read_fixed(8))[0]

    def read_length_prefixed_bytes(self) -> bytes:
        length = self.read_u32_be()
        return self.read_fixed(length)

    def read_length_prefixed_string(self) -> str:
        return self.read_length_prefixed_bytes().decode("utf-8")

    def expect_magic(self, expected: bytes) -> None:
        actual = self.read_fixed(len(expected))
        if actual != expected:
            raise ParseError(f"Invalid magic: expected {expected!r}, got {actual!r}.")
