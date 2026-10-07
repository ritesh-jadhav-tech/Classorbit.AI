from fastapi.testclient import TestClient


def test_register_login_and_access_authenticated_profile(client: TestClient) -> None:
    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Faculty User",
            "email": "faculty@classorbit.edu",
            "password": "1234",
            "role": "FACULTY",
        },
    )

    assert registration.status_code == 201, registration.text
    body = registration.json()
    assert body["user"]["email"] == "faculty@classorbit.edu"
    assert body["user"]["role"]["name"] == "FACULTY"
    assert body["token"]["token_type"] == "bearer"

    profile = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['token']['access_token']}"},
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["email"] == "faculty@classorbit.edu"

    login = client.post(
        "/api/auth/login",
        data={"username": "faculty@classorbit.edu", "password": "1234"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "name": "Faculty User",
        "email": "faculty@classorbit.edu",
        "password": "strong-password",
        "role": "FACULTY",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201

    duplicate = client.post("/api/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A user with this email already exists."


def test_register_accepts_each_role(client: TestClient) -> None:
    for role in ("ADMIN", "FACULTY", "EXAM_COORDINATOR"):
        response = client.post(
            "/api/auth/register",
            json={
                "name": f"{role} User",
                "email": f"{role.lower()}@classorbit.edu",
                "password": "strong-password",
                "role": role,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["user"]["role"]["name"] == role


def test_register_and_login_with_password_over_bcrypt_limit(client: TestClient) -> None:
    long_password = "test-password-" * 20
    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Long Password User",
            "email": "long-password@classorbit.edu",
            "password": long_password,
            "role": "FACULTY",
        },
    )
    assert registration.status_code == 201, registration.text

    login = client.post(
        "/api/auth/login",
        data={"username": "long-password@classorbit.edu", "password": long_password},
    )
    assert login.status_code == 200, login.text
