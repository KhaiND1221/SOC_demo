"""Seed script for demo data.

Run after `docker compose up -d` with:
    docker compose exec backend python -m app.seed
"""

from datetime import date, timedelta

from app.database import Base, SessionLocal, engine, wait_for_db
from app.models import Task, User
from app.security import hash_password

DEMO_PASSWORD = "Passw0rd!"

DEMO_USERS = [
    {"username": "alice", "email": "alice@example.com", "password": DEMO_PASSWORD},
    {"username": "bob", "email": "bob@example.com", "password": DEMO_PASSWORD},
    {"username": "carol", "email": "carol@example.com", "password": DEMO_PASSWORD},
]

TODAY = date.today()

DEMO_TASKS = {
    "alice": [
        {
            "title": "Chuẩn bị slide báo cáo tuần",
            "description": "Tổng hợp tiến độ công việc trong tuần",
            "priority": "high",
            "status": "doing",
            "category": "work",
            "due_date": TODAY + timedelta(days=2),
        },
        {
            "title": "Đọc tài liệu FastAPI logging",
            "description": None,
            "priority": "low",
            "status": "todo",
            "category": "study",
            "due_date": None,
        },
    ],
    "bob": [
        {
            "title": "Fix bug đăng nhập",
            "description": "Lỗi session hết hạn không revoke đúng",
            "priority": "medium",
            "status": "done",
            "category": "work",
            "due_date": TODAY - timedelta(days=1),
        },
    ],
    "carol": [],
}


def main():
    wait_for_db()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for user_data in DEMO_USERS:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if existing:
                print(f"User '{user_data['username']}' already exists, skipping.")
                continue

            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            tasks = DEMO_TASKS.get(user_data["username"], [])
            for task_data in tasks:
                db.add(Task(user_id=user.id, **task_data))
            db.commit()

            print(f"Created user '{user.username}' (id={user.id}) with {len(tasks)} task(s).")

        print(f"\nAll demo users share the password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
