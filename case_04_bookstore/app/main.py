from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine


app = FastAPI(title="Bookstore")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


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
        <title>Bookstore</title>
        <link rel="stylesheet" href="/static/css/style.css">
      </head>
      <body>
        <main class="page">
          <section class="hero">
            <p class="eyebrow">Case 04</p>
            <h1>Web-версия книжного магазина</h1>
            <p>Стартовая страница проекта. Следующие шаги: роли администратора и пользователя, каталог, сортировка, покупка и аренда книг.</p>
          </section>
        </main>
      </body>
    </html>
    """
