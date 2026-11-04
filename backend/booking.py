"""Subjects, tutor availability and lesson bookings."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError

from database import engine
from models import bookings, slots, subjects, tutor_subjects, users
from security import current_user, require_role

router = APIRouter(prefix="/api")
student_only = require_role("Student")
tutor_only = require_role("Tutor")

CANCEL_HOURS = 2      # students can cancel up to 2 hours before a lesson
MAX_UPCOMING = 10     # most upcoming lessons one student can hold


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return aware(dt).isoformat()


def short_name(first: str, last: str) -> str:
    return f"{first} {last[:1]}."   # "Thandi M." keeps surnames private


# ---------- input ----------

class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookingIn(_In):
    slot_id: int
    subject_id: int


class SlotIn(_In):
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def sensible_time(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Time zone required")
        v = v.astimezone(timezone.utc).replace(second=0, microsecond=0)
        if v < now() + timedelta(hours=1) or v > now() + timedelta(days=90):
            raise ValueError("Between 1 hour and 90 days from now")
        return v


class TutorSubjectsIn(_In):
    subject_ids: list[int] = Field(max_length=20)


# ---------- shared ----------

@router.get("/subjects")
def list_subjects(_: dict = Depends(current_user)):
    with engine.connect() as conn:
        rows = conn.execute(select(subjects).order_by(subjects.c.name)).mappings().all()
    return [{"id": r["id"], "name": r["name"]} for r in rows]


# ---------- students ----------

def _open_slots():
    """Slots joined with their booking (if any)."""
    return slots.outerjoin(bookings, bookings.c.slot_id == slots.c.id)


@router.get("/student/tutors")
def student_tutors(subject_id: int, _: dict = Depends(student_only)):
    open_count = (
        select(slots.c.tutor_id, func.count(slots.c.id).label("n"))
        .select_from(_open_slots())
        .where(bookings.c.id.is_(None), slots.c.starts_at > now())
        .group_by(slots.c.tutor_id)
        .subquery()
    )
    query = (
        select(users.c.id, users.c.first_name, users.c.last_name, open_count.c.n)
        .join(tutor_subjects, tutor_subjects.c.tutor_id == users.c.id)
        .join(open_count, open_count.c.tutor_id == users.c.id)
        .where(tutor_subjects.c.subject_id == subject_id,
               users.c.role == "Tutor", users.c.is_active.is_(True))
        .order_by(users.c.first_name)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [{"id": r[0], "name": short_name(r[1], r[2]), "open_slots": r[3]} for r in rows]


@router.get("/student/slots")
def student_slots(subject_id: int, tutor_id: int, _: dict = Depends(student_only)):
    with engine.connect() as conn:
        teaches = conn.execute(select(tutor_subjects).where(
            tutor_subjects.c.tutor_id == tutor_id,
            tutor_subjects.c.subject_id == subject_id)).first()
        if not teaches:
            return []
        rows = conn.execute(
            select(slots.c.id, slots.c.starts_at)
            .select_from(_open_slots())
            .where(slots.c.tutor_id == tutor_id, bookings.c.id.is_(None), slots.c.starts_at > now())
            .order_by(slots.c.starts_at).limit(60)
        ).all()
    return [{"id": r[0], "starts_at": iso(r[1])} for r in rows]


@router.post("/student/bookings", status_code=201)
def book_lesson(data: BookingIn, student: dict = Depends(student_only)):
    with engine.begin() as conn:
        slot = conn.execute(select(slots).where(slots.c.id == data.slot_id)).mappings().first()
        if not slot or aware(slot["starts_at"]) <= now():
            raise HTTPException(404, "That time is no longer available.")
        teaches = conn.execute(select(tutor_subjects).where(
            tutor_subjects.c.tutor_id == slot["tutor_id"],
            tutor_subjects.c.subject_id == data.subject_id)).first()
        tutor_active = conn.execute(
            select(users.c.is_active).where(users.c.id == slot["tutor_id"])).scalar()
        if not teaches or not tutor_active:
            raise HTTPException(400, "That tutor doesn't offer this subject.")
        upcoming = conn.execute(
            select(func.count()).select_from(bookings.join(slots, slots.c.id == bookings.c.slot_id))
            .where(bookings.c.student_id == student["id"], slots.c.starts_at > now())).scalar()
        if upcoming >= MAX_UPCOMING:
            raise HTTPException(400, f"You can have up to {MAX_UPCOMING} upcoming lessons.")
        try:
            conn.execute(insert(bookings).values(
                slot_id=data.slot_id, student_id=student["id"], subject_id=data.subject_id))
        except IntegrityError:
            raise HTTPException(409, "Sorry, that time was just booked by someone else.")
    return {"message": "Lesson booked."}


@router.get("/student/bookings")
def my_bookings(student: dict = Depends(student_only)):
    query = (
        select(bookings.c.id, slots.c.starts_at, subjects.c.name, users.c.first_name, users.c.last_name)
        .select_from(bookings
                     .join(slots, slots.c.id == bookings.c.slot_id)
                     .join(subjects, subjects.c.id == bookings.c.subject_id)
                     .join(users, users.c.id == slots.c.tutor_id))
        .where(bookings.c.student_id == student["id"])
        .order_by(slots.c.starts_at.desc()).limit(100)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [{"id": r[0], "starts_at": iso(r[1]), "subject": r[2], "tutor": short_name(r[3], r[4])}
            for r in rows]


@router.delete("/student/bookings/{booking_id}")
def cancel_booking(booking_id: int, student: dict = Depends(student_only)):
    with engine.begin() as conn:
        row = conn.execute(
            select(slots.c.starts_at)
            .select_from(bookings.join(slots, slots.c.id == bookings.c.slot_id))
            .where(bookings.c.id == booking_id, bookings.c.student_id == student["id"])).first()
        if not row:
            raise HTTPException(404, "Lesson not found.")
        if aware(row[0]) < now() + timedelta(hours=CANCEL_HOURS):
            raise HTTPException(400, f"Lessons can only be cancelled more than {CANCEL_HOURS} hours before they start.")
        conn.execute(delete(bookings).where(bookings.c.id == booking_id))
    return {"message": "Lesson cancelled."}


# ---------- tutors ----------

@router.get("/tutor/subjects")
def tutor_subjects_get(tutor: dict = Depends(tutor_only)):
    with engine.connect() as conn:
        everything = conn.execute(select(subjects).order_by(subjects.c.name)).mappings().all()
        mine = {r[0] for r in conn.execute(
            select(tutor_subjects.c.subject_id).where(tutor_subjects.c.tutor_id == tutor["id"]))}
    return [{"id": s["id"], "name": s["name"], "selected": s["id"] in mine} for s in everything]


@router.put("/tutor/subjects")
def tutor_subjects_set(data: TutorSubjectsIn, tutor: dict = Depends(tutor_only)):
    with engine.begin() as conn:
        valid = set()
        if data.subject_ids:
            valid = {r[0] for r in conn.execute(
                select(subjects.c.id).where(subjects.c.id.in_(data.subject_ids)))}
        conn.execute(delete(tutor_subjects).where(tutor_subjects.c.tutor_id == tutor["id"]))
        if valid:
            conn.execute(insert(tutor_subjects),
                         [{"tutor_id": tutor["id"], "subject_id": s} for s in valid])
    return {"message": "Subjects saved."}


@router.get("/tutor/slots")
def tutor_slots(tutor: dict = Depends(tutor_only)):
    query = (
        select(slots.c.id, slots.c.starts_at, bookings.c.id, subjects.c.name,
               users.c.first_name, users.c.last_name, users.c.contact_number)
        .select_from(slots
                     .outerjoin(bookings, bookings.c.slot_id == slots.c.id)
                     .outerjoin(subjects, subjects.c.id == bookings.c.subject_id)
                     .outerjoin(users, users.c.id == bookings.c.student_id))
        .where(slots.c.tutor_id == tutor["id"], slots.c.starts_at > now() - timedelta(hours=1))
        .order_by(slots.c.starts_at)
    )
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    return [{
        "id": r[0], "starts_at": iso(r[1]), "booked": r[2] is not None,
        "subject": r[3], "student": f"{r[4]} {r[5]}" if r[2] else None,
        "student_contact": r[6] if r[2] else None,
    } for r in rows]


@router.post("/tutor/slots", status_code=201)
def add_slot(data: SlotIn, tutor: dict = Depends(tutor_only)):
    try:
        with engine.begin() as conn:
            conn.execute(insert(slots).values(tutor_id=tutor["id"], starts_at=data.starts_at))
    except IntegrityError:
        raise HTTPException(409, "You already have a slot at that time.")
    return {"message": "Slot added."}


@router.delete("/tutor/slots/{slot_id}")
def remove_slot(slot_id: int, tutor: dict = Depends(tutor_only)):
    with engine.begin() as conn:
        owned = conn.execute(select(slots.c.id).where(
            slots.c.id == slot_id, slots.c.tutor_id == tutor["id"])).first()
        if not owned:
            raise HTTPException(404, "Slot not found.")
        conn.execute(delete(bookings).where(bookings.c.slot_id == slot_id))
        conn.execute(delete(slots).where(slots.c.id == slot_id))
    return {"message": "Slot removed."}