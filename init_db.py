# init_db.py — seed default data into MongoDB
from werkzeug.security import generate_password_hash
from db import get_db, init_indexes


def init_database():
    db = get_db()
    init_indexes()

    # ── Default users ─────────────────────────────────────────────────────────
    # NOTE: Do NOT include student_id key when it's None.
    # MongoDB sparse unique index skips MISSING fields but still indexes null,
    # so multiple null values would cause a DuplicateKeyError.
    default_users = [
        {
            "username":      "admin",
            "password_hash": generate_password_hash("admin123"),
            "role":          "admin",
            "full_name":     "System Administrator",
            "department":    "Administration",
            "email":         "admin@example.com",
        },
        {
            "username":      "teacher1",
            "password_hash": generate_password_hash("teacher123"),
            "role":          "teacher",
            "full_name":     "John Doe",
            "department":    "Computer Science",
            "email":         "teacher1@example.com",
        },
        {
            "username":      "student1",
            "password_hash": generate_password_hash("student123"),
            "role":          "student",
            "full_name":     "Alice Smith",
            "department":    "Computer Science",
            "email":         "student1@example.com",
        },
    ]

    for user in default_users:
        if not db.users.find_one({"username": user["username"]}):
            db.users.insert_one(user)
            print(f"  ✅ Created user: {user['username']}")

    # ── Default subject ───────────────────────────────────────────────────────
    if not db.subjects.find_one({"subject_name": "General"}):
        db.subjects.insert_one({
            "subject_name": "General",
            "department":   "General",
        })
        print("  ✅ Created subject: General")

    print("✅ Database initialised")


if __name__ == "__main__":
    init_database()