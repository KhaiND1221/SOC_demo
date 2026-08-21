"""Seed script for demo data.

Run after `docker compose up -d` with:
    docker compose exec backend python -m app.seed
"""

from decimal import Decimal

from app.database import Base, SessionLocal, engine, wait_for_db
from app.models import Order, User
from app.security import hash_password

DEMO_PASSWORD = "Passw0rd!"

DEMO_USERS = [
    {"username": "alice", "email": "alice@example.com", "password": DEMO_PASSWORD},
    {"username": "bob", "email": "bob@example.com", "password": DEMO_PASSWORD},
    {"username": "carol", "email": "carol@example.com", "password": DEMO_PASSWORD},
]

DEMO_ORDERS = {
    "alice": [
        {"product_name": "Laptop", "quantity": 1, "unit_price": Decimal("1200.00"), "status": "paid"},
        {"product_name": "Mouse", "quantity": 2, "unit_price": Decimal("25.50"), "status": "pending"},
    ],
    "bob": [
        {"product_name": "Keyboard", "quantity": 1, "unit_price": Decimal("75.00"), "status": "shipped"},
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

            orders = DEMO_ORDERS.get(user_data["username"], [])
            for order_data in orders:
                db.add(Order(user_id=user.id, **order_data))
            db.commit()

            print(f"Created user '{user.username}' (id={user.id}) with {len(orders)} order(s).")

        print(f"\nAll demo users share the password: {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
