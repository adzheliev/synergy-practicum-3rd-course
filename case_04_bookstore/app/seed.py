from decimal import Decimal

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Book, Category, User
from .security import hash_password


def get_or_create_user(db, username: str, password: str, role: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return user
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.flush()
    return user


def get_or_create_category(db, name: str) -> Category:
    category = db.scalar(select(Category).where(Category.name == name))
    if category:
        return category
    category = Category(name=name)
    db.add(category)
    db.flush()
    return category


def create_book(db, title: str, author: str, year: int, category: Category, price: str, description: str) -> None:
    if db.scalar(select(Book).where(Book.title == title, Book.author == author)):
        return
    db.add(
        Book(
            title=title,
            author=author,
            year=year,
            category_id=category.id,
            price=Decimal(price),
            description=description,
            status="available",
        )
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        get_or_create_user(db, "admin", "admin123", "admin")
        get_or_create_user(db, "reader", "reader123", "user")

        backend = get_or_create_category(db, "Backend")
        frontend = get_or_create_category(db, "Frontend")
        databases = get_or_create_category(db, "Databases")

        create_book(
            db,
            "FastAPI in Practice",
            "S. Developer",
            2024,
            backend,
            "1200.00",
            "Practical guide for building APIs and web services with FastAPI.",
        )
        create_book(
            db,
            "Modern JavaScript Interfaces",
            "A. Frontender",
            2023,
            frontend,
            "980.00",
            "Examples of building interactive user interfaces with vanilla JavaScript.",
        )
        create_book(
            db,
            "PostgreSQL for Applications",
            "D. Admin",
            2022,
            databases,
            "1500.00",
            "Database design, constraints, indexes, and transactional application logic.",
        )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

