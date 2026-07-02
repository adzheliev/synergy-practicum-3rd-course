from datetime import date, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Book, Category, Purchase, Rental, User
from .security import hash_password, read_signed_user_id, sign_user_id, verify_password


app = FastAPI(title="Bookstore")
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


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
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
    role = "admin" if db.scalar(select(func.count(User.id))) == 0 else "user"
    user = User(username=username, password_hash=hash_password(password), role=role)
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
def index(
    category: str | None = None,
    sort: str = "title",
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> str:
    query = select(Book).join(Book.category)
    if category:
        query = query.where(Category.name == category)
    if sort == "author":
        query = query.order_by(Book.author.asc(), Book.title.asc())
    elif sort == "year":
        query = query.order_by(Book.year.desc(), Book.title.asc())
    else:
        sort = "title"
        query = query.order_by(Book.title.asc())
    books = db.scalars(query).all()
    categories = db.scalars(select(Category).order_by(Category.name.asc())).all()
    category_links = "".join(
        f'<a class="chip {"active" if category == item.name else ""}" href="/?category={item.name}&sort={sort}">{item.name}</a>'
        for item in categories
    )
    book_cards = "".join(
        f"""
        <article class="book-card">
          <div>
            <p class="meta">{book.category.name} · {book.year}</p>
            <h2>{book.title}</h2>
            <p>{book.author}</p>
            <p>{book.description}</p>
          </div>
          <div class="book-footer">
            <strong>{book.price} ₽</strong>
            <span>{book.status}</span>
          </div>
          {book_actions(book, user)}
        </article>
        """
        for book in books
    ) or '<article class="book-card empty">Книги не найдены.</article>'
    account_panel = (
        f"""
        <form method="post" action="/logout" class="account">
          <span>{user.username} · {user.role}</span>
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
        <title>Bookstore</title>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <main class="page">
          <section class="hero">
            <p class="eyebrow">Case 04</p>
            <h1>Web-версия книжного магазина</h1>
            <p>Каталог книг с ролями пользователя и администратора, сортировкой, покупкой и арендой.</p>
            {account_panel}
          </section>
          <section class="toolbar">
            <div>
              <a class="chip {all_active}" href="/?sort={sort}">Все</a>
              {category_links}
            </div>
            <div>
              <a class="chip {title_active}" href="/?{category_query}sort=title">По названию</a>
              <a class="chip {author_active}" href="/?{category_query}sort=author">По автору</a>
              <a class="chip {year_active}" href="/?{category_query}sort=year">По году</a>
            </div>
          </section>
          <section class="book-grid">
            {book_cards}
          </section>
        </main>
      </body>
    </html>
    """.format(
        account_panel=account_panel,
        all_active="active" if category is None else "",
        category_links=category_links,
        category_query=f"category={category}&" if category else "",
        sort=sort,
        title_active="active" if sort == "title" else "",
        author_active="active" if sort == "author" else "",
        year_active="active" if sort == "year" else "",
        book_cards=book_cards,
    )


def book_actions(book: Book, user: User | None) -> str:
    if user is None:
        return '<p class="hint">Войдите, чтобы купить или арендовать книгу.</p>'
    if book.status != "available":
        return '<p class="hint">Книга сейчас недоступна.</p>'
    return f"""
    <div class="actions">
      <form method="post" action="/books/{book.id}/purchase">
        <button type="submit">Купить</button>
      </form>
      <form method="post" action="/books/{book.id}/rent">
        <select name="period_days">
          <option value="14">2 недели</option>
          <option value="30">1 месяц</option>
          <option value="90">3 месяца</option>
        </select>
        <button type="submit">Арендовать</button>
      </form>
    </div>
    """


@app.post("/books/{book_id}/purchase")
def purchase_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    book = db.get(Book, book_id)
    if book is None or book.status != "available":
        raise HTTPException(status_code=404, detail="Available book not found")
    db.add(Purchase(user_id=user.id, book_id=book.id, price=book.price))
    book.status = "sold"
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/books/{book_id}/rent")
def rent_book(
    book_id: int,
    period_days: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if period_days not in {14, 30, 90}:
        raise HTTPException(status_code=400, detail="Invalid rental period")
    book = db.get(Book, book_id)
    if book is None or book.status != "available":
        raise HTTPException(status_code=404, detail="Available book not found")
    today = date.today()
    db.add(
        Rental(
            user_id=user.id,
            book_id=book.id,
            start_date=today,
            end_date=today + timedelta(days=period_days),
            status="active",
        )
    )
    book.status = "rented"
    db.commit()
    return RedirectResponse("/", status_code=303)
