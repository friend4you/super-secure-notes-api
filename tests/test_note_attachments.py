import hashlib
import uuid

import pytest

from tests.fixtures import make_note_blob
from tests.support import create_note, expected_composite_etag, register_user


@pytest.mark.asyncio
async def test_body_only_fetch_and_lazy_attachment(client):
    user = await register_user(client, "attachments-lazy@example.com")
    note_id, body = await create_note(client, user["headers"])
    attachment_id = uuid.uuid4()
    attachment_data = bytes([0x42] * 2048)

    put = await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=attachment_data,
        params={"contentType": "image/jpeg"},
    )
    assert put.status_code == 200
    put_body = put.json()
    assert put_body["attachmentId"] == str(attachment_id)
    assert put_body["sizeBytes"] == len(attachment_data)
    assert put_body["contentType"] == "image/jpeg"
    assert put_body["noteEtag"] == expected_composite_etag(
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
    assert "data" not in items[0]

    got_attachment = await client.get(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers=user["headers"],
    )
    assert got_attachment.status_code == 200
    assert got_attachment.content == attachment_data

    listed = await client.get("/v1/notes", headers=user["headers"])
    assert listed.json()[0]["attachmentCount"] == 1
    assert listed.json()[0]["attachmentsTotalSize"] == len(attachment_data)
    assert listed.json()[0]["etag"] == put_body["noteEtag"]


@pytest.mark.asyncio
async def test_composite_etag_changes_on_attachment_add(client):
    user = await register_user(client, "attachments-etag@example.com")
    note_id, body = await create_note(client, user["headers"])
    before = expected_composite_etag(body)

    listed_before = await client.get("/v1/notes", headers=user["headers"])
    assert listed_before.json()[0]["etag"] == before

    attachment_id = uuid.uuid4()
    attachment_data = b"opaque-encrypted-bytes"
    put = await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=attachment_data,
    )
    assert put.status_code == 200
    assert put.json()["noteEtag"] != before
    assert put.json()["noteEtag"] == expected_composite_etag(
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
    await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=attachment_data,
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

    await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=attachment_data,
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
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers=user["headers"],
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_shared_lazy_attachment_download(client):
    alice = await register_user(client, "alice-lazy-share@example.com")
    bob = await register_user(client, "bob-lazy-share@example.com")
    note_id, body = await create_note(client, alice["headers"])
    attachment_id = uuid.uuid4()
    attachment_data = bytes([0x99] * 512)

    await client.put(
        f"/v1/notes/{note_id}/attachments/{attachment_id}",
        headers={**alice["headers"], "Content-Type": "application/octet-stream"},
        content=attachment_data,
    )

    from tests.support import WRAPPED_FEK_B64

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

    shared_attachment = await client.get(
        f"/v1/notes/shared/{note_id}/attachments/{attachment_id}",
        headers=bob["headers"],
    )
    assert shared_attachment.status_code == 200
    assert shared_attachment.content == attachment_data

    forbidden_put = await client.put(
        f"/v1/notes/shared/{note_id}/attachments/{attachment_id}",
        headers={**bob["headers"], "Content-Type": "application/octet-stream"},
        content=b"nope",
    )
    assert forbidden_put.status_code == 405
