import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    original = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": list(details["participants"]),
        }
        for name, details in activities.items()
    }

    activities.clear()
    activities.update(original)
    yield
    activities.clear()
    activities.update(original)


@pytest.fixture()
def client():
    return TestClient(app)


def test_get_activities_returns_activity_catalog(client):
    # Arrange
    # No special setup needed for this read-only request.

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert "Chess Club" in payload
    assert payload["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant_and_prevents_duplicate(client):
    # Arrange
    activity_name = "Chess Club"
    email = "newstudent@mergington.edu"

    # Act: first signup
    first_response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )

    # Assert: first signup succeeds
    assert first_response.status_code == 200
    assert first_response.json()["message"] == (
        f"Signed up {email} for {activity_name}"
    )

    # Act: duplicate signup
    duplicate_response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )

    # Assert: duplicate signup is rejected
    assert duplicate_response.status_code == 400
    assert "already signed up" in duplicate_response.json()["detail"].lower()


def test_signup_rejects_when_activity_is_full(client):
    # Arrange
    activity_name = "Chess Club"
    activity = activities[activity_name]
    available_slots = activity["max_participants"] - len(activity["participants"])

    # Act: fill the activity to capacity
    for index in range(available_slots):
        email = f"student{index}@mergington.edu"
        response = client.post(
            f"/activities/{activity_name.replace(' ', '%20')}/signup",
            params={"email": email},
        )
        assert response.status_code == 200

    # Act: attempt one more signup
    overflow_response = client.post(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": "overflow@mergington.edu"},
    )

    # Assert
    assert overflow_response.status_code == 400
    assert "full" in overflow_response.json()["detail"].lower()


def test_unregister_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name.replace(' ', '%20')}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == (
        f"Unregistered {email} from {activity_name}"
    )

    updated = client.get("/activities").json()[activity_name]
    assert email not in updated["participants"]
