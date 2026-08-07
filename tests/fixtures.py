import struct
import uuid


def _append_u32_be(buffer: bytearray, value: int) -> None:
    buffer.extend(struct.pack(">I", value))


def _append_u64_be(buffer: bytearray, value: int) -> None:
    buffer.extend(struct.pack(">Q", value))


def _append_length_prefixed_bytes(buffer: bytearray, data: bytes) -> None:
    _append_u32_be(buffer, len(data))
    buffer.extend(data)


def _append_length_prefixed_string(buffer: bytearray, value: str) -> None:
    _append_length_prefixed_bytes(buffer, value.encode("utf-8"))


def make_vault_header_v2(public_key: bytes | None = None) -> bytes:
    key = public_key or bytes([0x11] * 32)
    buffer = bytearray()
    buffer.extend(b"SSNV")
    buffer.append(2)  # version
    buffer.append(1)  # kdf_id
    buffer.extend(bytes([0xAA] * 32))  # salt
    _append_u32_be(buffer, 600_000)  # iterations
    _append_length_prefixed_bytes(buffer, bytes([0x01] * 60))
    _append_length_prefixed_bytes(buffer, bytes([0x02] * 60))
    buffer.append(1)  # identity_algorithm_id
    buffer.extend(key)
    _append_length_prefixed_bytes(buffer, bytes([0x22] * 60))
    return bytes(buffer)


def make_note_blob(
    note_id: uuid.UUID | None = None,
    title: str = "My note",
    updated_at: int = 1_700_000_100,
    encrypted_payload: bytes | None = None,
    attachment_count: int = 0,
    attachments_total_size: int = 0,
) -> bytes:
    note_id = note_id or uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    payload = encrypted_payload if encrypted_payload is not None else bytes([0xCD] * 128)
    buffer = bytearray()
    buffer.extend(b"SSNT")
    buffer.append(1)  # version
    buffer.extend(note_id.bytes)
    _append_length_prefixed_string(buffer, title)
    _append_u64_be(buffer, 1_700_000_000)  # created_at
    _append_u64_be(buffer, updated_at)
    _append_u32_be(buffer, attachment_count)
    _append_u64_be(buffer, attachments_total_size)
    _append_length_prefixed_bytes(buffer, bytes([0xAB] * 60))
    _append_length_prefixed_bytes(buffer, payload)
    return bytes(buffer)


def make_large_attachment(target_size: int = 12_582_912) -> bytes:
    return bytes([0xEE]) * target_size
