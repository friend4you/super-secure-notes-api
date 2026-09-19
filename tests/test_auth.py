import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_privacy_policy_page(client):
    for path in ("/privacy", "/privacy-policy"):
        response = await client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        body = response.text
        assert "Privacy Policy" in body
        assert "Super Secure Notes" in body
        assert "zero-knowledge" in body.lower() or "encrypted on your device" in body.lower()
        assert "delete your account" in body.lower()
        assert "vlad.arsenyuk@gmail.com" in body


@pytest.mark.asyncio
async def test_register_login_logout_refresh_flow(client, credentials):
    register = await client.post("/v1/auth/register", json=credentials)
    assert register.status_code == 201
    register_body = register.json()
    assert register_body["user"]["email"] == credentials["email"]
    assert register_body["accessToken"]
    assert register_body["refreshToken"]
    assert register_body["expiresIn"] == 900

    duplicate = await client.post("/v1/auth/register", json=credentials)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "email_already_exists"

    login = await client.post("/v1/auth/login", json=credentials)
    assert login.status_code == 200
    login_body = login.json()
    access_token = login_body["accessToken"]
    refresh_token = login_body["refreshToken"]

    bad_login = await client.post(
        "/v1/auth/login",
        json={"email": credentials["email"], "password": "wrong-password"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"] == "invalid_credentials"

    refreshed = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    assert refreshed_body["accessToken"] != access_token
    assert refreshed_body["refreshToken"] != refresh_token

    old_refresh = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert old_refresh.status_code == 401

    logout = await client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed_body['accessToken']}"},
    )
    assert logout.status_code == 204

    after_logout = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": refreshed_body["refreshToken"]},
    )
    assert after_logout.status_code == 401


@pytest.mark.asyncio
async def test_validation_error(client):
    response = await client.post("/v1/auth/register", json={"email": "not-an-email"})
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_delete_account_success(client, credentials):
    register = await client.post("/v1/auth/register", json=credentials)
    assert register.status_code == 201
    access_token = register.json()["accessToken"]
    refresh_token = register.json()["refreshToken"]

    deleted = await client.post(
        "/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": credentials["password"]},
    )
    assert deleted.status_code == 204

    login = await client.post("/v1/auth/login", json=credentials)
    assert login.status_code == 401
    assert login.json()["error"] == "invalid_credentials"

    protected = await client.get(
        "/v1/vault/header",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert protected.status_code == 401
    assert protected.json()["error"] == "unauthorized"
    assert protected.json()["message"] == "User not found."

    refresh = await client.post(
        "/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh.status_code == 401
    assert refresh.json()["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_delete_account_wrong_password(client, credentials):
    register = await client.post("/v1/auth/register", json=credentials)
    assert register.status_code == 201
    access_token = register.json()["accessToken"]

    deleted = await client.post(
        "/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": "wrong-password"},
    )
    assert deleted.status_code == 401
    assert deleted.json()["error"] == "invalid_credentials"

    login = await client.post("/v1/auth/login", json=credentials)
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_delete_account_re_register(client, credentials):
    register = await client.post("/v1/auth/register", json=credentials)
    assert register.status_code == 201
    old_user_id = register.json()["user"]["id"]
    access_token = register.json()["accessToken"]

    deleted = await client.post(
        "/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": credentials["password"]},
    )
    assert deleted.status_code == 204

    re_register = await client.post("/v1/auth/register", json=credentials)
    assert re_register.status_code == 201
    assert re_register.json()["user"]["id"] != old_user_id


@pytest.mark.asyncio
async def test_delete_account_cascade_vault_and_notes(client, credentials):
    from tests.support import create_note, register_user, vault_header_bytes

    user = await register_user(client, credentials["email"], credentials["password"])
    note_id, _ = await create_note(client, user["headers"])

    put_vault = await client.put(
        "/v1/vault/header",
        headers={**user["headers"], "Content-Type": "application/octet-stream"},
        content=vault_header_bytes(),
    )
    assert put_vault.status_code == 204

    deleted = await client.post(
        "/v1/auth/delete-account",
        headers=user["headers"],
        json={"password": credentials["password"]},
    )
    assert deleted.status_code == 204

    login = await client.post("/v1/auth/login", json=credentials)
    assert login.status_code == 401

    re_register = await client.post("/v1/auth/register", json=credentials)
    assert re_register.status_code == 201
    new_headers = {"Authorization": f"Bearer {re_register.json()['accessToken']}"}

    notes = await client.get("/v1/notes", headers=new_headers)
    assert notes.status_code == 200
    assert notes.json() == []

    vault = await client.get("/v1/vault/header", headers=new_headers)
    assert vault.status_code == 404
    assert vault.json()["error"] == "header_not_found"

    old_note = await client.get(f"/v1/notes/{note_id}/body", headers=new_headers)
    assert old_note.status_code == 404


@pytest.mark.asyncio
async def test_delete_account_removes_shared_notes_for_recipient(client):
    from tests.support import WRAPPED_FEK_B64, create_note, register_user

    alice = await register_user(client, "alice-delete@example.com")
    bob = await register_user(client, "bob-delete@example.com")
    note_id, _ = await create_note(client, alice["headers"])

    share = await client.post(
        f"/v1/notes/{note_id}/share",
        headers=alice["headers"],
        json={"recipientEmail": "bob-delete@example.com", "wrappedFek": WRAPPED_FEK_B64},
    )
    assert share.status_code == 201

    bob_shared = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert len(bob_shared.json()) == 1

    deleted = await client.post(
        "/v1/auth/delete-account",
        headers=alice["headers"],
        json={"password": "secret-password"},
    )
    assert deleted.status_code == 204

    bob_shared_after = await client.get("/v1/notes/shared", headers=bob["headers"])
    assert bob_shared_after.status_code == 200
    assert bob_shared_after.json() == []


@pytest.mark.asyncio
async def test_delete_account_validation_error(client, credentials):
    register = await client.post("/v1/auth/register", json=credentials)
    assert register.status_code == 201
    access_token = register.json()["accessToken"]

    missing_password = await client.post(
        "/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={},
    )
    assert missing_password.status_code == 400
    assert missing_password.json()["error"] == "validation_error"

    empty_password = await client.post(
        "/v1/auth/delete-account",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"password": ""},
    )
    assert empty_password.status_code == 400
    assert empty_password.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_delete_account_unauthenticated(client):
    response = await client.post(
        "/v1/auth/delete-account",
        json={"password": "secret-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
