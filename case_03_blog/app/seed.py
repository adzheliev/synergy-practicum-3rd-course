from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Comment, Post, PostAccessRequest, Subscription, Tag, User
from .security import hash_password


def get_or_create_user(db, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return user
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user


def get_or_create_tag(db, name: str) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.name == name))
    if tag:
        return tag
    tag = Tag(name=name)
    db.add(tag)
    db.flush()
    return tag


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        student = get_or_create_user(db, "student", "student123")
        mentor = get_or_create_user(db, "mentor", "mentor123")

        if not db.scalar(select(Post).where(Post.title == "FastAPI practice notes")):
            post = Post(
                title="FastAPI practice notes",
                body="Public post about building a web application with FastAPI, PostgreSQL, and vanilla JavaScript.",
                is_public=True,
                author_id=student.id,
            )
            post.tags = [get_or_create_tag(db, "fastapi"), get_or_create_tag(db, "practice")]
            db.add(post)
            db.flush()
            db.add(Comment(body="Good starting point for the practice report.", post_id=post.id, author_id=mentor.id))

        if not db.scalar(select(Post).where(Post.title == "Private project draft")):
            private_post = Post(
                title="Private project draft",
                body="This post is hidden until the author approves an access request.",
                is_public=False,
                author_id=student.id,
            )
            private_post.tags = [get_or_create_tag(db, "draft")]
            db.add(private_post)
            db.flush()
            db.add(PostAccessRequest(post_id=private_post.id, requester_id=mentor.id, status="pending"))

        if not db.scalar(select(Subscription).where(Subscription.subscriber_id == mentor.id, Subscription.author_id == student.id)):
            db.add(Subscription(subscriber_id=mentor.id, author_id=student.id))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()

