from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Trip, TripImage, TripRating, User
from .security import hash_password, read_signed_user_id, sign_user_id, verify_password


app = FastAPI(title="Travel Diary")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = read_signed_user_id(request.cookies.get("session"))
    if user_id is None:
        return None
    return db.get(User, user_id)


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    username = username.strip().lower()
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Username must be 3+ chars, password must be 6+ chars")
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=400, detail="Username is already taken")
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    redirect = RedirectResponse("/", status_code=303)
    redirect.set_cookie("session", sign_user_id(user.id), httponly=True, samesite="lax")
    return redirect


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    redirect = RedirectResponse("/", status_code=303)
    redirect.set_cookie("session", sign_user_id(user.id), httponly=True, samesite="lax")
    return redirect


@app.post("/logout")
def logout():
    redirect = RedirectResponse("/", status_code=303)
    redirect.delete_cookie("session")
    return redirect


@app.get("/", response_class=HTMLResponse)
def index(db: Session = Depends(get_db), user: User | None = Depends(get_current_user)) -> str:
    trips = db.scalars(
        select(Trip).where(Trip.is_public.is_(True)).order_by(Trip.created_at.desc())
    ).all()
    trip_cards = "".join(render_trip_card(trip) for trip in trips) or '<article class="trip-card empty">Пока нет публичных путешествий.</article>'
    account_panel = (
        f"""
        <form method="post" action="/logout" class="account">
          <span>{user.username}</span>
          <button type="submit">Выйти</button>
        </form>
        """
        if user
        else """
        <div class="auth-grid">
          <form method="post" action="/login" class="stack">
            <input name="username" placeholder="Логин" required>
            <input name="password" type="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
          </form>
          <form method="post" action="/register" class="stack">
            <input name="username" placeholder="Новый логин" required>
            <input name="password" type="password" placeholder="Пароль от 6 символов" required>
            <button type="submit">Зарегистрироваться</button>
          </form>
        </div>
        """
    )
    create_panel = (
        """
        <section class="trip-card">
          <h2>Новая запись</h2>
          <form method="post" action="/trips" class="trip-form">
            <input name="title" placeholder="Название путешествия" required>
            <input name="location" placeholder="Местоположение" required>
            <input name="latitude" type="number" step="0.000001" placeholder="Широта">
            <input name="longitude" type="number" step="0.000001" placeholder="Долгота">
            <input name="cost" type="number" min="0" step="0.01" placeholder="Стоимость">
            <input name="image_url" placeholder="URL изображения">
            <textarea name="heritage_places" placeholder="Места культурного наследия"></textarea>
            <textarea name="places_to_visit" placeholder="Места для посещения"></textarea>
            <textarea name="body" placeholder="Описание путешествия" required></textarea>
            <label class="check"><input type="checkbox" name="is_public" value="true" checked> Публичная запись</label>
            <div class="ratings">
              <input name="transport_score" type="number" min="1" max="5" value="5" required>
              <input name="safety_score" type="number" min="1" max="5" value="5" required>
              <input name="crowd_score" type="number" min="1" max="5" value="3" required>
              <input name="nature_score" type="number" min="1" max="5" value="5" required>
            </div>
            <button type="submit">Сохранить</button>
          </form>
        </section>
        """
        if user
        else ""
    )
    return """
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Travel Diary</title>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <main class="page">
          <section class="hero">
            <p class="eyebrow">Case 05</p>
            <h1>Дневник путешествий</h1>
            <p>Записи путешествий с геопозицией, изображениями, стоимостью, местами для посещения и оценками.</p>
            {account_panel}
          </section>
          {create_panel}
          <section class="trip-grid">
            {trip_cards}
          </section>
        </main>
      </body>
    </html>
    """.format(account_panel=account_panel, create_panel=create_panel, trip_cards=trip_cards)


def render_trip_card(trip: Trip) -> str:
    image = trip.images[0].image_url if trip.images else ""
    image_html = f'<img src="{image}" alt="{trip.title}">' if image else ""
    rating = trip.ratings[0] if trip.ratings else None
    rating_html = (
        f"""
        <p>Оценки: транспорт {rating.transport_score}/5, безопасность {rating.safety_score}/5,
        людность {rating.crowd_score}/5, природа {rating.nature_score}/5</p>
        """
        if rating
        else ""
    )
    geo = f"{trip.latitude}, {trip.longitude}" if trip.latitude is not None and trip.longitude is not None else "не указана"
    cost = f"{trip.cost} ₽" if trip.cost is not None else "не указана"
    return f"""
    <article class="trip-card">
      {image_html}
      <p class="meta">{trip.location}</p>
      <h2>{trip.title}</h2>
      <p>{trip.body}</p>
      <p>Геопозиция: {geo}</p>
      <p>Стоимость: {cost}</p>
      <p>Культурное наследие: {trip.heritage_places or "не указано"}</p>
      <p>Места для посещения: {trip.places_to_visit or "не указаны"}</p>
      {rating_html}
    </article>
    """


@app.post("/trips")
def create_trip(
    title: str = Form(...),
    location: str = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    cost: float | None = Form(None),
    image_url: str = Form(""),
    heritage_places: str = Form(""),
    places_to_visit: str = Form(""),
    body: str = Form(...),
    is_public: bool = Form(False),
    transport_score: int = Form(...),
    safety_score: int = Form(...),
    crowd_score: int = Form(...),
    nature_score: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    for score in [transport_score, safety_score, crowd_score, nature_score]:
        if score < 1 or score > 5:
            raise HTTPException(status_code=400, detail="Scores must be from 1 to 5")
    trip = Trip(
        title=title.strip(),
        location=location.strip(),
        latitude=latitude,
        longitude=longitude,
        cost=cost,
        heritage_places=heritage_places.strip(),
        places_to_visit=places_to_visit.strip(),
        body=body.strip(),
        is_public=is_public,
        author_id=user.id,
    )
    db.add(trip)
    db.flush()
    if image_url.strip():
        db.add(TripImage(trip_id=trip.id, image_url=image_url.strip()))
    db.add(
        TripRating(
            trip_id=trip.id,
            transport_score=transport_score,
            safety_score=safety_score,
            crowd_score=crowd_score,
            nature_score=nature_score,
        )
    )
    db.commit()
    return RedirectResponse("/", status_code=303)
