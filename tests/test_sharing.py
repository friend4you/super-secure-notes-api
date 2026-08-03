import base64
import uuid

import pytest

from tests.fixtures import make_note_blob

WRAPPED_FEK_B64 = base64.b64encode(bytes([0xAB] * 60)).decode("ascii")


async def register_user(client, email: str, password: str = "secret-password") -> dict:
    response = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['accessToken']}"},
        "user_id": body["user"]["id"],
        "email": body["user"]["email"],
    }


async def create_note(client, headers: dict, note_id: uuid.UUID | None = None) -> tuple[uuid.UUID, bytes]:
    note_id = note_id or uuid.uuid4()
    blob = make_note_blob(note_id=note_id)
    response = await client.put(
        f"/v1/notes/{note_id}",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=blob,
    )
    assert response.status_code == 200
    return note_id, blob


@pytest.mark.asyncio
async def test_share_flow_between_users(client):
    alice = await register_user(client, "alice@example.com")
    bob = await register_user(client, "bob@example.com")
    note_id, blob = await create_note(client, alice["headers"])

    share = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "bob@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert share.status_code == 201
    share_body = share.json()
    assert share_body["recipientEmail"] == "bob@example.com"
    assert share_body["shareId"]

    listed = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert listed.status_code == 200
    summaries = listed.json()
    assert len(summaries) == 1
    assert summaries[0]["noteId"] == str(note_id)
    assert summaries[0]["ownerEmail"] == "alice@example.com"
    assert summaries[0]["ownerId"] == alice["user_id"]

    download = await client.get(f"/v1/notes/shared/{note_id}", headers=bob["headers"])
    assert download.status_code == 200
    download_body = download.json()
    assert download_body["noteId"] == str(note_id)
    assert download_body["wrappedFek"] == WRAPPED_FEK_B64
    assert base64.b64decode(download_body["blob"]) == blob

    updated_blob = make_note_blob(note_id=note_id, title="Updated title", updated_at=1_700_000_200)
    update = await client.put(
        f"/v1/notes/{note_id}",
        headers={**alice["headers"], "Content-Type": "application/octet-stream"},
        content=updated_blob,
    )
    assert update.status_code == 200

    refreshed = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert refreshed.json()[0]["updatedAt"] == 1_700_000_200

    removed = await client.delete(f"/v1/notes/shared/{note_id}", headers=bob["headers"])
    assert removed.status_code == 204

    empty = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert empty.json() == []

    alice_note = await client.get(f"/v1/notes/{note_id}", headers=alice["headers"])
    assert alice_note.status_code == 200


@pytest.mark.asyncio
async def test_share_validation_errors(client):
    alice = await register_user(client, "owner@example.com")
    note_id, _ = await create_note(client, alice["headers"])

    self_share = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "owner@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert self_share.status_code == 400
    assert self_share.json()["error"] == "validation_error"

    missing_user = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "nobody@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["error"] == "user_not_found"

    await register_user(client, "recipient@example.com")
    first = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "recipient@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert first.status_code == 201

    duplicate = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "recipient@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "already_shared"


@pytest.mark.asyncio
async def test_owner_revokes_share(client):
    alice = await register_user(client, "alice-revoke@example.com")
    bob = await register_user(client, "bob-revoke@example.com")
    note_id, _ = await create_note(client, alice["headers"])

    await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "bob-revoke@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )

    revoke = await client.delete(
        f"/v1/notes/{note_id}/share/bob-revoke@example.com",
        headers=alice["headers"],
    )
    assert revoke.status_code == 204

    listed = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert listed.json() == []

    missing = await client.delete(
        f"/v1/notes/{note_id}/share/bob-revoke@example.com",
        headers=alice["headers"],
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "share_not_found"
