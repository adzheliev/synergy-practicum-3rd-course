from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User
from .security import read_signed_user_id


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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
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
            <p>Стартовая страница проекта. Следующие шаги: пользователи, записи путешествий, публичный просмотр, геолокация, изображения, стоимость и оценки.</p>
          </section>
        </main>
      </body>
    </html>
    """
