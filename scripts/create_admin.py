from getpass import getpass

from app.core.database import SessionLocal
from app.services.auth_service import create_admin_user, get_admin_by_email


def main():
    db = SessionLocal()

    try:
        email = input("Admin email: ").strip().lower()
        full_name = input("Full name (optional): ").strip() or None
        password = getpass("Admin password: ")
        confirm_password = getpass("Confirm password: ")

        if not email:
            print("Email is required")
            return

        if password != confirm_password:
            print("Passwords do not match")
            return

        if len(password) < 6:
            print("Password must be at least 6 characters long")
            return

        existing_user = get_admin_by_email(db, email)
        if existing_user is not None:
            print("Admin user already exists")
            return

        user = create_admin_user(
            db=db,
            email=email,
            password=password,
            full_name=full_name,
            is_superuser=True,
        )

        print("Admin user created successfully")
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()