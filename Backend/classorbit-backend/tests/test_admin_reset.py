from fastapi.testclient import TestClient


def test_admin_can_reset_test_data_with_password(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    department = client.post(
        "/api/departments",
        headers=admin_headers,
        json={"name": "Arts", "code": "ARTS"},
    )
    assert department.status_code == 201, department.text

    user = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "name": "Faculty User",
            "email": "faculty@classorbit.edu",
            "password": "faculty-password",
            "role": "FACULTY",
            "department_id": department.json()["id"],
        },
    )
    assert user.status_code == 201, user.text

    classroom = client.post(
        "/api/classrooms",
        headers=admin_headers,
        json={"room_number": "CC 4", "display_name": "Classroom CC 4"},
    )
    assert classroom.status_code == 201, classroom.text

    csv_content = (
        "class_name,division,day,start_time,end_time,subject,room\n"
        "FYBA,A,Monday,07:15,08:15,Hindi,CC 4\n"
    ).encode()
    imported = client.post(
        "/api/imports",
        headers=admin_headers,
        files={"file": ("fyba.csv", csv_content, "text/csv")},
    )
    assert imported.status_code == 201, imported.text

    wrong_password = client.post(
        "/api/admin/test-data/reset",
        headers=admin_headers,
        json={"password": "wrong-password"},
    )
    assert wrong_password.status_code == 403
    assert client.get("/api/timetable-entries", headers=admin_headers).json()

    response = client.post(
        "/api/admin/test-data/reset",
        headers=admin_headers,
        json={"password": "strong-password"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_deleted"] > 0
    assert payload["preserved_users"] == 2
    assert payload["deleted_counts"]["timetable_entries"] == 1

    for path in (
        "/api/imports",
        "/api/timetables",
        "/api/timetable-entries",
        "/api/time-slots",
        "/api/classrooms",
        "/api/subjects",
        "/api/departments",
        "/api/faculty",
        "/api/allocations",
    ):
        result = client.get(path, headers=admin_headers)
        assert result.status_code == 200, result.text
        assert result.json() == []

    users = client.get("/api/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()) == 2
    assert all(item["department_id"] is None for item in users.json())


def test_non_admin_cannot_reset_test_data(client: TestClient) -> None:
    registration = client.post(
        "/api/auth/register",
        json={
            "name": "Faculty User",
            "email": "faculty@classorbit.edu",
            "password": "faculty-password",
            "role": "FACULTY",
        },
    )
    token = registration.json()["token"]["access_token"]

    response = client.post(
        "/api/admin/test-data/reset",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "faculty-password"},
    )
    assert response.status_code == 403

