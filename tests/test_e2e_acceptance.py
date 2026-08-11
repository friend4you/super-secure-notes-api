"""E2E acceptance tests from docs/SPEC.md §9."""

import base64
import uuid

import pytest

from tests.fixtures import make_note_blob
from tests.support import (
    WRAPPED_FEK_B64,
    create_note,
    download_attachment_chunks,
    large_attachment_bytes,
    login_user,
    register_user,
    upload_attachment_chunks,
    vault_header_bytes,
)


@pytest.mark.asyncio
async def test_acceptance_1_register_vault_note_roundtrip(client):
    user = await register_user(client, "acceptance-1@example.com")
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440010")

    vault = await client.put(
        "/v1/vault/header",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=vault_header_bytes(),
    )
    assert vault.status_code == 204

    note_id, blob = await create_note(client, user["headers"], note_id=note_id)

    got = await client.get(f"/v1/notes/{note_id}/body", headers=user["headers"])
    assert got.status_code == 200
    assert got.content == blob


@pytest.mark.asyncio
async def test_acceptance_2_second_device_lists_and_downloads_note(client):
    email = "acceptance-2@example.com"
    password = "secret-password"
    await register_user(client, email, password)
    device_a = await login_user(client, email, password)
    note_id, blob = await create_note(client, device_a["headers"])

    device_b = await login_user(client, email, password)
    listed = await client.get("/v1/notes", headers=device_b["headers"])
    assert listed.status_code == 200
    assert any(item["noteId"] == str(note_id) for item in listed.json())

    got = await client.get(f"/v1/notes/{note_id}/body", headers=device_b["headers"])
    assert got.status_code == 200
    assert got.content == blob


@pytest.mark.asyncio
async def test_acceptance_3_if_match_conflict(client):
    user = await register_user(client, "acceptance-3@example.com")
    note_id, blob = await create_note(client, user["headers"])

    conflict = await client.put(
        f"/v1/notes/{note_id}/body",
        headers={
            **user["headers"],
            "Content-Type": "application/octet-stream",
            "If-Match": '"wrong-etag"',
        },
        content=blob,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "conflict"


@pytest.mark.asyncio
async def test_acceptance_4_chunked_attachment_upload(client):
    user = await register_user(client, "acceptance-4@example.com")
    note_id, _ = await create_note(client, user["headers"])
    attachment_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440011")
    data = large_attachment_bytes()

    await upload_attachment_chunks(client, user["headers"], note_id, attachment_id, data)

    manifest = await client.get(
        f"/v1/notes/{note_id}/attachments",
        headers=user["headers"],
    )
    total_chunks = manifest.json()[0]["totalChunks"]
    downloaded = await download_attachment_chunks(
        client, user["headers"], note_id, attachment_id, total_chunks
    )
    assert downloaded == data
    assert len(downloaded) > 10_485_760


@pytest.mark.asyncio
async def test_acceptance_5_alice_shares_bob_downloads(client):
    alice = await register_user(client, "alice-acceptance-5@example.com")
    bob = await register_user(client, "bob-acceptance-5@example.com")
    note_id, blob = await create_note(client, alice["headers"])

    share = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": bob["email"], "wrappedFek": WRAPPED_FEK_B64},
    )
    assert share.status_code == 201

    download = await client.get(f"/v1/notes/shared/{note_id}", headers=bob["headers"])
    assert download.status_code == 200
    body = download.json()
    assert body["wrappedFek"] == WRAPPED_FEK_B64
    assert base64.b64decode(body["body"]) == blob


@pytest.mark.asyncio
async def test_acceptance_6_shared_list_reflects_owner_update(client):
    alice = await register_user(client, "alice-acceptance-6@example.com")
    bob = await register_user(client, "bob-acceptance-6@example.com")
    note_id, _ = await create_note(client, alice["headers"])

    await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": bob["email"], "wrappedFek": WRAPPED_FEK_B64},
    )

    updated_blob = make_note_blob(note_id=note_id, title="Updated", updated_at=1_800_000_000)
    await client.put(
        f"/v1/notes/{note_id}/body",
        headers={**alice["headers"], "Content-Type": "application/octet-stream"},
        content=updated_blob,
    )

    listed = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert listed.json()[0]["updatedAt"] == 1_800_000_000


@pytest.mark.asyncio
async def test_acceptance_7_bob_removes_share_alice_keeps_note(client):
    alice = await register_user(client, "alice-acceptance-7@example.com")
    bob = await register_user(client, "bob-acceptance-7@example.com")
    note_id, _ = await create_note(client, alice["headers"])

    await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": bob["email"], "wrappedFek": WRAPPED_FEK_B64},
    )

    removed = await client.delete(f"/v1/notes/shared/{note_id}", headers=bob["headers"])
    assert removed.status_code == 204

    listed = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert listed.json() == []

    alice_note = await client.get(f"/v1/notes/{note_id}/body", headers=alice["headers"])
    assert alice_note.status_code == 200


@pytest.mark.asyncio
async def test_acceptance_8_refresh_token_rotation(client):
    user = await register_user(client, "acceptance-8@example.com")
    old_refresh = user["refresh_token"]

    refreshed = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refreshToken"]
    assert new_refresh != old_refresh

    stale = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert stale.status_code == 401
