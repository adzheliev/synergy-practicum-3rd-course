from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User
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
def index(user: User | None = Depends(get_current_user)) -> str:
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
            {account_panel}
          </section>
        </main>
      </body>
    </html>
    """.format(account_panel=account_panel)
