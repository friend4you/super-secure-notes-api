import uuid
from dataclasses import dataclass

from app.parsers.buffer import ByteReader, ParseError

SSNT_MAGIC = b"SSNT"
NOTE_ID_LENGTH = 16


@dataclass(frozen=True)
class NoteMetadata:
    note_id: uuid.UUID
    title: str
    updated_at: int


def _read_note_id(reader: ByteReader) -> uuid.UUID:
    raw = reader.read_fixed(NOTE_ID_LENGTH)
    return uuid.UUID(bytes=raw)


def parse_note_blob(data: bytes) -> NoteMetadata:
    if not data:
        raise ParseError("Empty note blob.")

    reader = ByteReader(data)
    reader.expect_magic(SSNT_MAGIC)

    version = reader.read_u8()
    if version != 1:
        raise ParseError(f"Unsupported note format version: {version}.")

    note_id = _read_note_id(reader)
    title = reader.read_length_prefixed_string()
    reader.read_u64_be()  # created_at
    updated_at = reader.read_u64_be()
    reader.read_u32_be()  # attachment_count
    reader.read_u64_be()  # attachments_total_size
    reader.read_length_prefixed_bytes()  # wrapped_fek
    reader.read_length_prefixed_bytes()  # encrypted_payload

    if not reader.at_end:
        raise ParseError("Note blob contains trailing bytes.")

    return NoteMetadata(note_id=note_id, title=title, updated_at=updated_at)
