import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
