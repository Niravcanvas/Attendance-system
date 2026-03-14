# db.py — MongoDB connection layer
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB   = os.environ.get("MONGO_DB",  "attendance_system")

_client = None
_db     = None


def get_db():
    global _client, _db
    if _db is not None:
        return _db
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    _db = _client[MONGO_DB]
    return _db


def init_indexes():
    """Create all indexes (call once at startup)."""
    db = get_db()

    # users
    db.users.create_index("username", unique=True)
    db.users.create_index("student_id", unique=True, sparse=True)

    # students
    db.students.create_index(
        "roll_no", unique=True, sparse=True
    )  # sparse so NULL roll_no doesn't conflict

    # sessions
    db.sessions.create_index([("subject_id", ASCENDING), ("date", ASCENDING)])
    db.sessions.create_index("teacher_id")

    # attendance — compound unique on (session_id, student_id)
    db.attendance.create_index(
        [("session_id", ASCENDING), ("student_id", ASCENDING)],
        unique=True,
    )
    db.attendance.create_index("student_id")
    db.attendance.create_index("session_id")

    print("✅ MongoDB indexes created")


def ping():
    """Return True if MongoDB is reachable."""
    try:
        get_db().command("ping")
        return True
    except ConnectionFailure:
        return False