import uuid

import pytest

from app.parsers.buffer import ParseError
from app.parsers.ssnv import parse_vault_header
from app.parsers.ssnt import parse_note_blob
from tests.fixtures import make_note_blob, make_vault_header_v2


def test_parse_vault_header_v2():
    header = make_vault_header_v2()
    metadata = parse_vault_header(header)
    assert metadata.format_version == 2
    assert metadata.public_key == bytes([0x11] * 32)
    assert metadata.algorithm_id == 1


def test_parse_vault_header_rejects_invalid_magic():
    with pytest.raises(ParseError):
        parse_vault_header(b"XXXX")


def test_parse_note_blob():
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    blob = make_note_blob(note_id=note_id, title="My note", updated_at=1_700_000_100)
    metadata = parse_note_blob(blob)
    assert metadata.note_id == note_id
    assert metadata.title == "My note"
    assert metadata.updated_at == 1_700_000_100
