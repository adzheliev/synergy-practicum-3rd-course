from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, get_db
from .models import Comment, Post, PostAccessRequest, Subscription, Tag, User
from .security import hash_password, read_signed_user_id, sign_user_id, verify_password

app = FastAPI(title="Student Blog")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


def parse_tags(raw_tags: str, db: Session) -> list[Tag]:
    names = sorted({tag.strip().lower() for tag in raw_tags.split(",") if tag.strip()})
    result = []
    for name in names:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        result.append(tag)
    return result


def visible_posts_query(user: User | None):
    if user is None:
        return select(Post).where(Post.is_public.is_(True))
    approved_posts = select(PostAccessRequest.post_id).where(
        PostAccessRequest.requester_id == user.id,
        PostAccessRequest.status == "approved",
    )
    return select(Post).where(or_(Post.is_public.is_(True), Post.author_id == user.id, Post.id.in_(approved_posts)))


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    tag: str | None = None,
    sort: str = "newest",
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
) -> HTMLResponse:
    query = visible_posts_query(user).options(
        selectinload(Post.author),
        selectinload(Post.tags),
        selectinload(Post.comments).selectinload(Comment.author),
    )
    if tag:
        query = query.join(Post.tags).where(Tag.name == tag.lower())
    if sort == "oldest":
        query = query.order_by(Post.created_at.asc())
    elif sort == "title":
        query = query.order_by(Post.title.asc())
    else:
        sort = "newest"
        query = query.order_by(Post.created_at.desc())
    posts = db.scalars(query).unique().all()
    tags = db.scalars(select(Tag).order_by(Tag.name)).all()
    users = db.scalars(select(User).order_by(User.username)).all()
    subscribed_author_ids = set()
    if user:
        subscribed_author_ids = set(
            db.scalars(select(Subscription.author_id).where(Subscription.subscriber_id == user.id)).all()
        )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": user,
            "posts": posts,
            "tags": tags,
            "users": users,
            "active_tag": tag,
            "active_sort": sort,
            "subscribed_author_ids": subscribed_author_ids,
        },
    )


@app.get("/feed", response_class=HTMLResponse)
def feed(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> HTMLResponse:
    author_ids = select(Subscription.author_id).where(Subscription.subscriber_id == user.id)
    posts = db.scalars(
        select(Post)
        .where(Post.author_id.in_(author_ids), Post.is_public.is_(True))
        .options(selectinload(Post.author), selectinload(Post.tags), selectinload(Post.comments).selectinload(Comment.author))
        .order_by(Post.created_at.desc())
    ).all()
    return templates.TemplateResponse("feed.html", {"request": request, "current_user": user, "posts": posts})


@app.get("/private", response_class=HTMLResponse)
def private_posts(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> HTMLResponse:
    approved_posts = select(PostAccessRequest.post_id).where(
        PostAccessRequest.requester_id == user.id,
        PostAccessRequest.status == "approved",
    )
    posts = db.scalars(
        select(Post)
        .where(Post.is_public.is_(False), Post.author_id != user.id, Post.id.not_in(approved_posts))
        .options(selectinload(Post.author), selectinload(Post.tags))
        .order_by(Post.created_at.desc())
    ).all()
    my_requests = db.scalars(
        select(PostAccessRequest)
        .join(Post)
        .where(Post.author_id == user.id, PostAccessRequest.status == "pending")
        .options(selectinload(PostAccessRequest.post), selectinload(PostAccessRequest.requester))
        .order_by(PostAccessRequest.created_at.desc())
    ).all()
    sent_requests = db.scalars(
        select(PostAccessRequest)
        .where(PostAccessRequest.requester_id == user.id)
        .options(selectinload(PostAccessRequest.post))
    ).all()
    sent_by_post = {item.post_id: item for item in sent_requests}
    return templates.TemplateResponse(
        "private.html",
        {
            "request": request,
            "current_user": user,
            "posts": posts,
            "my_requests": my_requests,
            "sent_by_post": sent_by_post,
        },
    )


@app.post("/register")
def register(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
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


@app.post("/posts")
def create_post(
    title: str = Form(...),
    body: str = Form(...),
    tags: str = Form(""),
    is_public: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = Post(title=title.strip(), body=body.strip(), is_public=is_public, author_id=user.id)
    post.tags = parse_tags(tags, db)
    db.add(post)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/posts/{post_id}/edit")
def edit_post(
    post_id: int,
    title: str = Form(...),
    body: str = Form(...),
    tags: str = Form(""),
    is_public: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = db.get(Post, post_id)
    if post is None or post.author_id != user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    post.title = title.strip()
    post.body = body.strip()
    post.is_public = is_public
    post.tags = parse_tags(tags, db)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/posts/{post_id}/delete")
def delete_post(post_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    post = db.get(Post, post_id)
    if post is None or post.author_id != user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    body: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = db.get(Post, post_id)
    has_access = db.scalar(
        select(
            exists().where(
                PostAccessRequest.post_id == post_id,
                PostAccessRequest.requester_id == user.id,
                PostAccessRequest.status == "approved",
            )
        )
    )
    if post is None or (not post.is_public and post.author_id != user.id and not has_access):
        raise HTTPException(status_code=404, detail="Post not found")
    db.add(Comment(body=body.strip(), post_id=post.id, author_id=user.id))
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/comments/{comment_id}/delete")
def delete_comment(comment_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    comment = db.scalar(select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.post)))
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != user.id and comment.post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db.delete(comment)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/users/{author_id}/subscribe")
def subscribe(author_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if author_id == user.id or db.get(User, author_id) is None:
        raise HTTPException(status_code=400, detail="Invalid author")
    exists_query = select(
        exists().where(Subscription.subscriber_id == user.id, Subscription.author_id == author_id)
    )
    if not db.scalar(exists_query):
        db.add(Subscription(subscriber_id=user.id, author_id=author_id))
        db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/users/{author_id}/unsubscribe")
def unsubscribe(author_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    subscription = db.scalar(
        select(Subscription).where(Subscription.subscriber_id == user.id, Subscription.author_id == author_id)
    )
    if subscription:
        db.delete(subscription)
        db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/posts/{post_id}/request-access")
def request_post_access(post_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    post = db.get(Post, post_id)
    if post is None or post.is_public or post.author_id == user.id:
        raise HTTPException(status_code=400, detail="Invalid private post")
    existing = db.scalar(
        select(PostAccessRequest).where(PostAccessRequest.post_id == post_id, PostAccessRequest.requester_id == user.id)
    )
    if existing is None:
        db.add(PostAccessRequest(post_id=post_id, requester_id=user.id))
        db.commit()
    return RedirectResponse("/private", status_code=303)


@app.post("/access-requests/{request_id}/approve")
def approve_post_access(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    access_request = db.scalar(
        select(PostAccessRequest)
        .join(Post)
        .where(PostAccessRequest.id == request_id, Post.author_id == user.id)
    )
    if access_request is None:
        raise HTTPException(status_code=404, detail="Access request not found")
    access_request.status = "approved"
    db.commit()
    return RedirectResponse("/private", status_code=303)


@app.post("/access-requests/{request_id}/reject")
def reject_post_access(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    access_request = db.scalar(
        select(PostAccessRequest)
        .join(Post)
        .where(PostAccessRequest.id == request_id, Post.author_id == user.id)
    )
    if access_request is None:
        raise HTTPException(status_code=404, detail="Access request not found")
    access_request.status = "rejected"
    db.commit()
    return RedirectResponse("/private", status_code=303)
