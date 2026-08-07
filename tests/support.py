import base64
import uuid

from app.notes.service import compute_composite_etag, compute_etag
from tests.fixtures import make_large_attachment, make_note_blob, make_vault_header_v2

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
        "refresh_token": body["refreshToken"],
        "user_id": body["user"]["id"],
        "email": body["user"]["email"],
    }


async def login_user(client, email: str, password: str = "secret-password") -> dict:
    response = await client.post(
        "/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['accessToken']}"},
        "refresh_token": body["refreshToken"],
    }


async def create_note(
    client,
    headers: dict,
    note_id: uuid.UUID | None = None,
    blob: bytes | None = None,
) -> tuple[uuid.UUID, bytes]:
    note_id = note_id or uuid.uuid4()
    blob = blob if blob is not None else make_note_blob(note_id=note_id)
    response = await client.put(
        f"/v1/notes/{note_id}/body",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=blob,
    )
    assert response.status_code == 200
    return note_id, blob


async def upload_attachment_chunks(
    client,
    headers: dict,
    note_id: uuid.UUID,
    attachment_id: uuid.UUID,
    data: bytes,
) -> None:
    from app.notes.constants import CHUNK_SIZE_BYTES

    init = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads",
        headers=headers,
        json={"totalSize": len(data), "contentType": "application/octet-stream"},
    )
    assert init.status_code == 201
    upload_id = init.json()["uploadId"]
    total_chunks = init.json()["totalChunks"]

    offset = 0
    for index in range(total_chunks):
        if index < total_chunks - 1:
            chunk = data[offset : offset + CHUNK_SIZE_BYTES]
        else:
            chunk = data[offset:]
        offset += len(chunk)
        put = await client.put(
            f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/chunks/{index}",
            headers={**headers, "Content-Type": "application/octet-stream"},
            content=chunk,
        )
        assert put.status_code == 204

    complete = await client.post(
        f"/v1/notes/{note_id}/attachments/{attachment_id}/uploads/{upload_id}/complete",
        headers=headers,
        json={},
    )
    assert complete.status_code == 200


def vault_header_bytes() -> bytes:
    return make_vault_header_v2()


def large_attachment_bytes(target_size: int = 12_582_912) -> bytes:
    return make_large_attachment(target_size=target_size)


def expected_composite_etag(
    body: bytes,
    attachments: list[tuple[uuid.UUID, bytes]] | None = None,
) -> str:
    pairs = [
        (attachment_id, compute_etag(data))
        for attachment_id, data in (attachments or [])
    ]
    return compute_composite_etag(compute_etag(body), pairs)
