from datetime import datetime, timedelta, timezone

from .conftest import login, register


def in_days(n):
    return (datetime.now(timezone.utc) + timedelta(days=n)).replace(second=0, microsecond=0).isoformat()


def tutor_with_slot(client):
    register(client, email="tutor@example.com", username="tutor1", role="Tutor",
             first_name="Thandi", last_name="Mokoena")
    login(client, email="tutor@example.com")
    subject_id = client.get("/api/subjects").json()[0]["id"]
    assert client.put("/api/tutor/subjects", json={"subject_ids": [subject_id]}).status_code == 200
    assert client.post("/api/tutor/slots", json={"starts_at": in_days(2)}).status_code == 201
    client.post("/api/logout")
    return subject_id


def test_booking_flow(client):
    subject_id = tutor_with_slot(client)
    register(client)
    login(client)

    tutors = client.get(f"/api/student/tutors?subject_id={subject_id}").json()
    assert [t["name"] for t in tutors] == ["Thandi M."]
    slots = client.get(f"/api/student/slots?subject_id={subject_id}&tutor_id={tutors[0]['id']}").json()
    assert len(slots) == 1

    body = {"slot_id": slots[0]["id"], "subject_id": subject_id}
    assert client.post("/api/student/bookings", json=body).status_code == 201
    assert client.post("/api/student/bookings", json=body).status_code == 409   # no double booking

    mine = client.get("/api/student/bookings").json()
    assert len(mine) == 1 and mine[0]["tutor"] == "Thandi M."
    assert client.delete(f"/api/student/bookings/{mine[0]['id']}").status_code == 200
    assert len(client.get(f"/api/student/slots?subject_id={subject_id}&tutor_id={tutors[0]['id']}").json()) == 1


def test_roles_are_separated(client):
    tutor_with_slot(client)
    register(client)
    login(client)
    assert client.get("/api/tutor/slots").status_code == 403
    assert client.post("/api/tutor/slots", json={"starts_at": in_days(3)}).status_code == 403
    client.post("/api/logout")
    assert client.get("/api/student/bookings").status_code == 401


def test_slot_must_be_in_the_future_and_have_timezone(client):
    register(client, role="Tutor")
    login(client)
    assert client.post("/api/tutor/slots", json={"starts_at": in_days(-1)}).status_code == 422
    assert client.post("/api/tutor/slots", json={"starts_at": "2030-01-01T10:00:00"}).status_code == 422