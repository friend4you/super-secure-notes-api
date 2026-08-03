import hashlib
import uuid

import pytest

from tests.fixtures import make_note_blob, make_vault_header_v2


@pytest.fixture
async def auth_headers(client, credentials):
    response = await client.post("/v1/auth/register", json=credentials)
    assert response.status_code == 201
    token = response.json()["accessToken"]
    user_id = response.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.mark.asyncio
async def test_vault_header_flow(client, auth_headers):
    headers, user_id = auth_headers
    missing = await client.get("/v1/vault/header", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"] == "header_not_found"

    vault_bytes = make_vault_header_v2()
    put = await client.put(
        "/v1/vault/header",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=vault_bytes,
    )
    assert put.status_code == 204

    got = await client.get("/v1/vault/header", headers=headers)
    assert got.status_code == 200
    assert got.content == vault_bytes

    pubkey = await client.get(f"/v1/users/{user_id}/public-key", headers=headers)
    assert pubkey.status_code == 200
    assert pubkey.json()["algorithmId"] == 1


@pytest.mark.asyncio
async def test_notes_crud_flow(client, auth_headers):
    headers, _ = auth_headers
    note_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    blob = make_note_blob(note_id=note_id)

    empty = await client.get("/v1/notes", headers=headers)
    assert empty.status_code == 200
    assert empty.json() == []

    put = await client.put(
        f"/v1/notes/{note_id}",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=blob,
    )
    assert put.status_code == 200
    body = put.json()
    assert body["syncState"] == "synced"
    assert body["updatedAt"] == 1_700_000_100
    assert body["etag"] == hashlib.sha256(blob).hexdigest()

    listed = await client.get("/v1/notes", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["noteId"] == str(note_id)

    got = await client.get(f"/v1/notes/{note_id}", headers=headers)
    assert got.status_code == 200
    assert got.content == blob
    assert got.headers["etag"] == f'"{body["etag"]}"'

    conflict = await client.put(
        f"/v1/notes/{note_id}",
        headers={
            **headers,
            "Content-Type": "application/octet-stream",
            "If-Match": '"wrong-etag"',
        },
        content=blob,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "conflict"

    deleted = await client.delete(f"/v1/notes/{note_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/v1/notes/{note_id}", headers=headers)
    assert missing.status_code == 404
