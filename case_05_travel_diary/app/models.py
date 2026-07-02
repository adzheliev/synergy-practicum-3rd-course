from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trips: Mapped[list["Trip"]] = relationship(back_populates="author", cascade="all, delete-orphan")


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    location: Mapped[str] = mapped_column(String(160), index=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    heritage_places: Mapped[str] = mapped_column(Text, default="")
    places_to_visit: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    author: Mapped[User] = relationship(back_populates="trips")
    images: Mapped[list["TripImage"]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    ratings: Mapped[list["TripRating"]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class TripImage(Base):
    __tablename__ = "trip_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_url: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str] = mapped_column(String(160), default="")
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)

    trip: Mapped[Trip] = relationship(back_populates="images")


class TripRating(Base):
    __tablename__ = "trip_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transport_score: Mapped[int] = mapped_column(Integer)
    safety_score: Mapped[int] = mapped_column(Integer)
    crowd_score: Mapped[int] = mapped_column(Integer)
    nature_score: Mapped[int] = mapped_column(Integer)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)

    trip: Mapped[Trip] = relationship(back_populates="ratings")

