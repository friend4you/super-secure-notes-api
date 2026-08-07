import uuid

import pytest

from app.notes.constants import CHUNK_SIZE_BYTES
from tests.support import create_note, large_attachment_bytes, register_user


@pytest.fixture
async def auth_headers(client, credentials):
    user = await register_user(client, credentials["email"], credentials["password"])
    return user["headers"]


@pytest.mark.asyncio
async def test_init_upload_rejects_small_size(client, auth_headers):
    note_id, _ = await create_note(client, auth_headers)
    attachment_id = uuid.uuid4()
    response = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads",
        headers=auth_headers,
        json={"totalSize": 10_485_760, "contentType": "application/octet-stream"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_chunked_upload_completes_large_attachment(client, auth_headers):
    note_id, _ = await create_note(client, auth_headers)
    attachment_id = uuid.UUID("550e8400-e29b-41d4-a716-4466554400aa")
    data = large_attachment_bytes()
    assert len(data) > 10_485_760

    init = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(data), "contentType": "application/octet-stream"},
    )
    assert init.status_code == 201
    init_body = init.json()
    upload_id = init_body["uploadId"]
    assert init_body["chunkSize"] == CHUNK_SIZE_BYTES
    assert init_body["totalChunks"] == 3

    offset = 0
    for index in range(init_body["totalChunks"]):
        if index < init_body["totalChunks"] - 1:
            chunk = data[offset : offset + CHUNK_SIZE_BYTES]
        else:
            chunk = data[offset:]
        offset += len(chunk)

        put = await client.put(
            f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/chunks/{index}",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
            content=chunk,
        )
        assert put.status_code == 204

    complete = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/complete",
        headers=auth_headers,
        json={},
    )
    assert complete.status_code == 200
    assert complete.json()["attachmentId"] == str(attachment_id)
    assert complete.json()["sizeBytes"] == len(data)

    got = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers=auth_headers,
    )
    assert got.status_code == 200
    assert got.content == data


@pytest.mark.asyncio
async def test_new_upload_aborts_previous_session(client, auth_headers):
    note_id, _ = await create_note(client, auth_headers)
    attachment_id = uuid.UUID("550e8400-e29b-41d4-a716-4466554400ab")
    data = large_attachment_bytes()

    first = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(data), "contentType": "application/octet-stream"},
    )
    assert first.status_code == 201
    first_upload_id = first.json()["uploadId"]

    second = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(data), "contentType": "application/octet-stream"},
    )
    assert second.status_code == 201
    assert second.json()["uploadId"] != first_upload_id

    stale_chunk = await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads/{first_upload_id}/chunks/0",
        headers={**auth_headers, "Content-Type": "application/octet-stream"},
        content=data[:CHUNK_SIZE_BYTES],
    )
    assert stale_chunk.status_code == 409
