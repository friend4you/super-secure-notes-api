import uuid

import pytest

from app.notes.constants import CHUNK_SIZE_BYTES
from tests.fixtures import make_large_note_blob


@pytest.fixture
async def auth_headers(client, credentials):
    response = await client.post("/v1/auth/register", json=credentials)
    assert response.status_code == 201
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_init_upload_rejects_small_size(client, auth_headers):
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
    response = await client.post(
        f"/v1/notes/{note_id}/uploads",
        headers=auth_headers,
        json={"totalSize": 10_485_760, "contentType": "application/octet-stream"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_chunked_upload_completes_large_note(client, auth_headers):
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
    blob = make_large_note_blob(note_id=note_id)
    assert len(blob) > 10_485_760

    init = await client.post(
        f"/v1/notes/{note_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(blob), "contentType": "application/octet-stream"},
    )
    assert init.status_code == 201
    init_body = init.json()
    upload_id = init_body["uploadId"]
    assert init_body["chunkSize"] == CHUNK_SIZE_BYTES
    assert init_body["totalChunks"] == 3

    offset = 0
    for index in range(init_body["totalChunks"]):
        if index < init_body["totalChunks"] - 1:
            chunk = blob[offset : offset + CHUNK_SIZE_BYTES]
        else:
            chunk = blob[offset:]
        offset += len(chunk)

        put = await client.put(
            f"/v1/notes/{note_id}/uploads/{upload_id}/chunks/{index}",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
            content=chunk,
        )
        assert put.status_code == 204

    complete = await client.post(
        f"/v1/notes/{note_id}/uploads/{upload_id}/complete",
        headers=auth_headers,
        json={},
    )
    assert complete.status_code == 200
    assert complete.json()["syncState"] == "synced"

    got = await client.get(f"/v1/notes/{note_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.content == blob


@pytest.mark.asyncio
async def test_new_upload_aborts_previous_session(client, auth_headers):
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440003")
    blob = make_large_note_blob(note_id=note_id)

    first = await client.post(
        f"/v1/notes/{note_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(blob), "contentType": "application/octet-stream"},
    )
    assert first.status_code == 201
    first_upload_id = first.json()["uploadId"]

    second = await client.post(
        f"/v1/notes/{note_id}/uploads",
        headers=auth_headers,
        json={"totalSize": len(blob), "contentType": "application/octet-stream"},
    )
    assert second.status_code == 201
    assert second.json()["uploadId"] != first_upload_id

    stale_chunk = await client.put(
        f"/v1/notes/{note_id}/uploads/{first_upload_id}/chunks/0",
        headers={**auth_headers, "Content-Type": "application/octet-stream"},
        content=blob[:CHUNK_SIZE_BYTES],
    )
    assert stale_chunk.status_code == 409
