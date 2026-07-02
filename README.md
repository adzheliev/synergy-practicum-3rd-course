# Synergy Practicum 3rd Course

Repository for production practice projects for the Web Development profile.

## Project Structure

- `case_03_blog/` - blog web application.
- `case_04_bookstore/` - bookstore web application scaffold.
- `case_05_travel_diary/` - travel diary web application scaffold.

Each project is self-contained and has its own:

- `README.md`
- `requirements.txt`
- `docker-compose.yml`
- PostgreSQL database instance

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- HTML/CSS/JavaScript
- Docker Compose

## Run All Projects

From the repository root:

```bash
docker compose up --build
```

Application URLs:

- Blog: `http://localhost:8003`
- Bookstore: `http://localhost:8004`
- Travel diary: `http://localhost:8005`

Database ports:

- Blog PostgreSQL: `localhost:5433`
- Bookstore PostgreSQL: `localhost:5434`
- Travel diary PostgreSQL: `localhost:5435`

## Run One Project

Each project can also be started independently from its own folder:

```bash
cd case_03_blog
docker compose up --build
```

```bash
cd case_04_bookstore
docker compose up --build
```

```bash
cd case_05_travel_diary
docker compose up --build
```

## Repository Rules

Practice report files in `.docx` format are kept locally and are not committed to the repository.
