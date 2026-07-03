from datetime import date, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

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


@app.get("/my-library", response_class=HTMLResponse)
def my_library(db: Session = Depends(get_db), user: User = Depends(require_user)) -> str:
    purchases = db.scalars(
        select(Purchase)
        .where(Purchase.user_id == user.id)
        .options(selectinload(Purchase.book))
        .order_by(Purchase.created_at.desc())
    ).all()
    rentals = db.scalars(
        select(Rental)
        .where(Rental.user_id == user.id)
        .options(selectinload(Rental.book))
        .order_by(Rental.end_date.asc())
    ).all()
    purchase_rows = "".join(
        f"<li>{item.book.title} — куплено за {item.price} ₽</li>"
        for item in purchases
    ) or "<li>Покупок пока нет.</li>"
    rental_rows = "".join(
        f"<li>{item.book.title} — аренда до {item.end_date}, статус: {item.status}</li>"
        for item in rentals
    ) or "<li>Аренд пока нет.</li>"
    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#1c1410">
        <title>Моя библиотека</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <header class="site-header">
          <a class="site-brand" href="/">Libra<span>rium</span></a>
          <nav class="site-nav"><a href="/">Каталог</a></nav>
        </header>
        <main class="page">
          <section class="hero">
            <div class="hero-inner">
              <p class="eyebrow">Моя библиотека</p>
              <h1>{user.username}</h1>
              <p><a href="/">Вернуться в каталог</a></p>
            </div>
          </section>
          <section class="book-card">
            <h2>Покупки</h2>
            <ul>{purchase_rows}</ul>
          </section>
          <section class="book-card">
            <h2>Аренда</h2>
            <ul>{rental_rows}</ul>
          </section>
        </main>
      </body>
    </html>
    """


@app.post("/admin/books")
def create_book(
    title: str = Form(...),
    author: str = Form(...),
    year: int = Form(...),
    category_name: str = Form(...),
    price: float = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    category_name = category_name.strip()
    category = db.scalar(select(Category).where(Category.name == category_name))
    if category is None:
        category = Category(name=category_name)
        db.add(category)
        db.flush()
    db.add(
        Book(
            title=title.strip(),
            author=author.strip(),
            year=year,
            category_id=category.id,
            price=price,
            description=description.strip(),
            status="available",
        )
    )
    db.commit()
    return RedirectResponse("/", status_code=303)


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
          {admin_book_controls(book, user)}
        </article>
        """
        for book in books
    ) or '<article class="book-card empty">Книги не найдены.</article>'
    account_panel = (
        f"""
        <form method="post" action="/logout" class="account">
          <span>{user.username} · {user.role}</span>
          <a href="/my-library">Моя библиотека</a>
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
    admin_panel = (
        """
        <section class="book-card">
          <h2>Добавить книгу</h2>
          <p><a href="/admin/rental-reminders">Напоминания об аренде</a></p>
          <form method="post" action="/admin/books" class="admin-form">
            <input name="title" placeholder="Название" required>
            <input name="author" placeholder="Автор" required>
            <input name="year" type="number" placeholder="Год" required>
            <input name="category_name" placeholder="Категория" required>
            <input name="price" type="number" min="0" step="0.01" placeholder="Цена" required>
            <textarea name="description" placeholder="Описание"></textarea>
            <button type="submit">Добавить</button>
          </form>
        </section>
        """
        if user and user.role == "admin"
        else ""
    )
    return """
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#1c1410">
        <title>Bookstore — Librarium</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <header class="site-header">
          <a class="site-brand" href="/">Libra<span>rium</span></a>
          <nav class="site-nav"><a href="/">Каталог</a>{nav_library}</nav>
        </header>
        <main class="page">
          <section class="hero">
            <div class="hero-inner">
              <p class="eyebrow">Антикварная коллекция</p>
              <h1>Книжный магазин</h1>
              <p>Каталог с покупкой и арендой, фильтрами по категориям и ролями пользователя и администратора.</p>
              {account_panel}
            </div>
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
          {admin_panel}
        </main>
      </body>
    </html>
    """.format(
        account_panel=account_panel,
        nav_library=' <a href="/my-library">Моя библиотека</a>' if user else "",
        all_active="active" if category is None else "",
        category_links=category_links,
        category_query=f"category={category}&" if category else "",
        sort=sort,
        title_active="active" if sort == "title" else "",
        author_active="active" if sort == "author" else "",
        year_active="active" if sort == "year" else "",
        book_cards=book_cards,
        admin_panel=admin_panel,
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


def admin_book_controls(book: Book, user: User | None) -> str:
    if user is None or user.role != "admin":
        return ""
    status_options = "".join(
        f'<option value="{status}" {"selected" if book.status == status else ""}>{status}</option>'
        for status in ["available", "rented", "sold", "hidden"]
    )
    return f"""
    <details>
      <summary>Управление</summary>
      <form method="post" action="/admin/books/{book.id}/update" class="admin-inline">
        <input name="price" type="number" min="0" step="0.01" value="{book.price}" required>
        <select name="status">{status_options}</select>
        <button type="submit">Сохранить</button>
      </form>
    </details>
    """


@app.post("/admin/books/{book_id}/update")
def update_book(
    book_id: int,
    price: float = Form(...),
    status_value: str = Form(..., alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    if status_value not in {"available", "rented", "sold", "hidden"}:
        raise HTTPException(status_code=400, detail="Invalid book status")
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    book.price = price
    book.status = status_value
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/admin/rental-reminders", response_class=HTMLResponse)
def rental_reminders(db: Session = Depends(get_db), user: User = Depends(require_admin)) -> str:
    today = date.today()
    soon = today + timedelta(days=3)
    rentals = db.scalars(
        select(Rental)
        .where(Rental.status == "active", Rental.end_date <= soon)
        .options(selectinload(Rental.book), selectinload(Rental.user))
        .order_by(Rental.end_date.asc())
    ).all()
    reminder_rows = "".join(
        f"<li>{item.user.username}: {item.book.title} — вернуть до {item.end_date}</li>"
        for item in rentals
    ) or "<li>Нет аренд, по которым требуется напоминание.</li>"
    return f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="theme-color" content="#1c1410">
        <title>Напоминания об аренде</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <header class="site-header">
          <a class="site-brand" href="/">Libra<span>rium</span></a>
          <nav class="site-nav"><a href="/">Каталог</a></nav>
        </header>
        <main class="page">
          <section class="hero">
            <div class="hero-inner">
              <p class="eyebrow">Администратор</p>
              <h1>Напоминания об окончании аренды</h1>
              <p>Показаны активные аренды, которые заканчиваются до {soon} включительно.</p>
              <p><a href="/">Вернуться в каталог</a></p>
            </div>
          </section>
          <section class="book-card">
            <ul>{reminder_rows}</ul>
          </section>
        </main>
      </body>
    </html>
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
