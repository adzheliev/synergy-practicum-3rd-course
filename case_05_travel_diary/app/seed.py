from decimal import Decimal

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Trip, TripImage, TripRating, User
from .security import hash_password


def get_or_create_user(db, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return user
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user


def create_trip(
    db,
    author: User,
    title: str,
    location: str,
    latitude: str,
    longitude: str,
    cost: str,
    image_url: str,
    body: str,
    heritage_places: str,
    places_to_visit: str,
    scores: tuple[int, int, int, int],
) -> None:
    if db.scalar(select(Trip).where(Trip.title == title, Trip.author_id == author.id)):
        return
    trip = Trip(
        title=title,
        location=location,
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        cost=Decimal(cost),
        body=body,
        heritage_places=heritage_places,
        places_to_visit=places_to_visit,
        is_public=True,
        author_id=author.id,
    )
    db.add(trip)
    db.flush()
    db.add(TripImage(trip_id=trip.id, image_url=image_url, caption=location))
    db.add(
        TripRating(
            trip_id=trip.id,
            transport_score=scores[0],
            safety_score=scores[1],
            crowd_score=scores[2],
            nature_score=scores[3],
        )
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        traveler = get_or_create_user(db, "traveler", "traveler123")
        friend = get_or_create_user(db, "friend", "friend123")

        create_trip(
            db,
            traveler,
            "Weekend in Saint Petersburg",
            "Saint Petersburg",
            "59.934280",
            "30.335099",
            "28500.00",
            "https://images.unsplash.com/photo-1556610961-2fecc5927173?auto=format&fit=crop&w=1200&q=80",
            "A short cultural route with museums, embankments, and long evening walks.",
            "Hermitage, Peter and Paul Fortress",
            "Nevsky Prospect, Summer Garden, New Holland",
            (5, 4, 3, 4),
        )
        create_trip(
            db,
            friend,
            "Mountain route in Sochi",
            "Sochi",
            "43.585472",
            "39.723099",
            "42000.00",
            "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
            "A mountain and sea trip focused on viewpoints, nature, and active walking.",
            "Olympic Park",
            "Rosa Khutor, Arboretum, seafront promenade",
            (4, 5, 4, 5),
        )

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

