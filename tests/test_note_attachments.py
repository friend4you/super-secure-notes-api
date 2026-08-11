import hashlib
import uuid

import pytest

from app.notes.constants import CHUNK_SIZE_BYTES
from tests.fixtures import make_note_blob
from tests.support import (
    create_note,
    download_attachment_chunks,
    expected_composite_etag,
    register_user,
    upload_attachment_chunks,
    WRAPPED_FEK_B64,
)


@pytest.mark.asyncio
async def test_body_only_fetch_and_lazy_attachment(client):
    user = await register_user(client, "attachments-lazy@example.com")
    note_id, body = await create_note(client, user["headers"])
    attachment_id = uuid.uuid4()
    attachment_data = bytes([0x42] * 2048)

    put = await upload_attachment_chunks(
        client,
        user["headers"],
        note_id,
        attachment_id,
        attachment_data,
        content_type="image/jpeg",
    )
    assert put["attachmentId"] == str(attachment_id)
    assert put["sizeBytes"] == len(attachment_data)
    assert put["contentType"] == "image/jpeg"
    assert put["noteEtag"] == expected_composite_etag(
        body, [(attachment_id, attachment_data)]
    )

    got_body = await client.get(f"/v1/notes/{note_id}/body", headers=user["headers"])
    assert got_body.status_code == 200
    assert got_body.content == body
    assert got_body.headers["etag"] == f'"{hashlib.sha256(body).hexdigest()}"'

    manifest = await client.get(
        f"/v1/notes/{note_id}/attachments",
        headers=user["headers"],
    )
    assert manifest.status_code == 200
    items = manifest.json()
    assert len(items) == 1
    assert items[0]["attachmentId"] == str(attachment_id)
    assert items[0]["sizeBytes"] == len(attachment_data)
    assert items[0]["contentType"] == "image/jpeg"
    assert items[0]["totalChunks"] == 1
    assert items[0]["chunkSize"] == CHUNK_SIZE_BYTES
    assert "data" not in items[0]

    got_attachment = await download_attachment_chunks(
        client, user["headers"], note_id, attachment_id, total_chunks=1
    )
    assert got_attachment == attachment_data

    listed = await client.get("/v1/notes", headers=user["headers"])
    assert listed.json()[0]["attachmentCount"] == 1
    assert listed.json()[0]["attachmentsTotalSize"] == len(attachment_data)
    assert listed.json()[0]["etag"] == put["noteEtag"]


@pytest.mark.asyncio
async def test_composite_etag_changes_on_attachment_add(client):
    user = await register_user(client, "attachments-etag@example.com")
    note_id, body = await create_note(client, user["headers"])
    before = expected_composite_etag(body)

    listed_before = await client.get("/v1/notes", headers=user["headers"])
    assert listed_before.json()[0]["etag"] == before

    attachment_id = uuid.uuid4()
    attachment_data = b"opaque-encrypted-bytes"
    put = await upload_attachment_chunks(
        client, user["headers"], note_id, attachment_id, attachment_data
    )
    assert put["noteEtag"] != before
    assert put["noteEtag"] == expected_composite_etag(
        body, [(attachment_id, attachment_data)]
    )


@pytest.mark.asyncio
async def test_manifest_validation_on_body_put(client):
    user = await register_user(client, "attachments-manifest@example.com")
    note_id = uuid.uuid4()
    body = make_note_blob(note_id=note_id, attachment_count=0, attachments_total_size=0)
    await create_note(client, user["headers"], note_id=note_id, blob=body)

    attachment_id = uuid.uuid4()
    attachment_data = bytes([0x11] * 100)
    await upload_attachment_chunks(
        client, user["headers"], note_id, attachment_id, attachment_data
    )

    mismatched = make_note_blob(
        note_id=note_id,
        attachment_count=2,
        attachments_total_size=100,
    )
    bad = await client.put(
        f"/v1/notes/{note_id}/body",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=mismatched,
    )
    assert bad.status_code == 400
    assert bad.json()["error"] == "validation_error"

    matched = make_note_blob(
        note_id=note_id,
        attachment_count=1,
        attachments_total_size=100,
    )
    ok = await client.put(
        f"/v1/notes/{note_id}/body",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=matched,
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_attachment_delete_and_not_found(client):
    user = await register_user(client, "attachments-delete@example.com")
    note_id, body = await create_note(client, user["headers"])
    attachment_id = uuid.uuid4()
    attachment_data = b"to-delete"

    await upload_attachment_chunks(
        client, user["headers"], note_id, attachment_id, attachment_data
    )

    deleted = await client.delete(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers=user["headers"],
    )
    assert deleted.status_code == 204

    listed = await client.get("/v1/notes", headers=user["headers"])
    assert listed.json()[0]["etag"] == expected_composite_etag(body)
    assert listed.json()[0]["attachmentCount"] == 0

    missing = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/chunks/0",
        headers=user["headers"],
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_chunk_download_first_last_invalid(client):
    user = await register_user(client, "attachments-chunks@example.com")
    note_id, _ = await create_note(client, user["headers"])
    attachment_id = uuid.uuid4()
    data = bytes(range(256)) * 40000  # ~10 MB, 2 chunks

    complete = await upload_attachment_chunks(
        client, user["headers"], note_id, attachment_id, data
    )
    total_chunks = (len(data) + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES

    first = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/chunks/0",
        headers=user["headers"],
    )
    assert first.status_code == 200
    assert len(first.content) == CHUNK_SIZE_BYTES
    assert first.headers["etag"] == f'"{complete["etag"]}"'

    last_index = total_chunks - 1
    last = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/chunks/{last_index}",
        headers=user["headers"],
    )
    assert last.status_code == 200
    assert len(last.content) == len(data) - CHUNK_SIZE_BYTES * last_index

    invalid = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/chunks/{total_chunks}",
        headers=user["headers"],
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_shared_lazy_attachment_download(client):
    alice = await register_user(client, "alice-lazy-share@example.com")
    bob = await register_user(client, "bob-lazy-share@example.com")
    note_id, body = await create_note(client, alice["headers"])
    attachment_id = uuid.uuid4()
    attachment_data = bytes([0x99] * 512)

    await upload_attachment_chunks(
        client, alice["headers"], note_id, attachment_id, attachment_data
    )

    share = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": bob["email"], "wrappedFek": WRAPPED_FEK_B64},
    )
    assert share.status_code == 201

    shared_body = await client.get(
        f"/v1/notes/shared/{note_id}/body",
        headers=bob["headers"],
    )
    assert shared_body.status_code == 200
    assert shared_body.content == body

    manifest = await client.get(
        f"/v1/notes/shared/{note_id}/attachments",
        headers=bob["headers"],
    )
    assert manifest.status_code == 200
    assert len(manifest.json()) == 1
    assert manifest.json()[0]["attachmentId"] == str(attachment_id)
    assert manifest.json()[0]["totalChunks"] == 1

    shared_attachment = await download_attachment_chunks(
        client,
        bob["headers"],
        note_id,
        attachment_id,
        total_chunks=1,
        shared=True,
    )
    assert shared_attachment == attachment_data

    forbidden_put = await client.put(
        f"/v1/notes/shared/{note_id}/attachments/{attachment_id}/uploads",
        headers={**bob["headers"], "Content-Type": "application/octet-stream"},
        json={"totalSize": 4, "contentType": "application/octet-stream"},
    )
    assert forbidden_put.status_code in (404, 405)


@pytest.mark.asyncio
async def test_upload_etag_matches_full_hash(client):
    user = await register_user(client, "attachments-etag-hash@example.com")
    note_id, _ = await create_note(client, user["headers"])
    attachment_id = uuid.uuid4()
    data = bytes([0xAB] * 5000)

    complete = await upload_attachment_chunks(
        client, user["headers"], note_id, attachment_id, data
    )
    assert complete["etag"] == hashlib.sha256(data).hexdigest()
