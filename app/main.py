from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os

from app.database import get_db
from app.models import User, Article, Comment
from app.schemas import UserCreate, ArticleCreate, ArticleUpdate, CommentCreate, CommentUpdate
from app.crud import (
    create_user,
    create_article,
    update_article,
    delete_article,
    create_comment,
    update_comment,
    delete_comment,
)
from passlib.context import CryptContext

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="app/templates")

# 세션 미들웨어 설정
load_dotenv()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

# 사용자 등록 함수 (비동기)
async def register_user(db: AsyncSession, user_in: UserCreate):
    hashed_password = pwd_context.hash(user_in.userPasswordHash)
    db_user = User(
        userID=user_in.userID,
        userName=user_in.userName,
        userPasswordHash=hashed_password,
        userCountry=user_in.userCountry,
        userLanguage=user_in.userLanguage,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# 회원가입 폼
@app.get("/signup/", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# 회원가입 처리
@app.post("/signup/")
async def signup(
    userID: str = Form(...),
    userName: str = Form(...),
    userPasswordHash: str = Form(...),
    userCountry: str = Form(...),
    userLanguage: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).filter(User.userID == userID))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists.")

    user_in = UserCreate(
        userID=userID,
        userName=userName,
        userPasswordHash=userPasswordHash,
        userCountry=userCountry,
        userLanguage=userLanguage,
    )
    new_user = await register_user(db, user_in)
    return {"message": "회원 가입이 완료되었습니다.", "user": new_user}

# 로그인 폼 및 처리
@app.get("/login/", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login/")
async def login(
    request: Request,
    userID: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.userID == userID))
    user = result.scalars().first()
    if not user or not pwd_context.verify(password, user.userPasswordHash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=400,
        )
    request.session["user"] = user.userID
    return RedirectResponse(url="/articles/", status_code=303)

# 로그아웃
@app.get("/logout/")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

# 글 목록
@app.get("/articles/", response_class=HTMLResponse)
async def list_articles(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).order_by(Article.createdAt.desc()))
    articles = result.scalars().all()
    return templates.TemplateResponse(
        "articles.html", {"request": request, "articles": articles}
    )

# 글 상세 및 댓글 목록
@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail(
    request: Request, article_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comments_result = await db.execute(
        select(Comment)
        .where(Comment.articleID == article_id)
        .order_by(Comment.createdAt.asc())
    )
    comments = comments_result.scalars().all()
    return templates.TemplateResponse(
        "article_detail.html",
        {"request": request, "article": article, "comments": comments},
    )

# 글 생성
@app.get("/create_article/", response_class=HTMLResponse)
async def create_article_page(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login/", status_code=303)
    return templates.TemplateResponse("create_article.html", {"request": request})

@app.post("/create_article/")
async def create_article_post(
    request: Request,
    articleTitle: str = Form(...),
    imageURL: str = Form(None),
    travelCountry: str = Form(...),
    travelCity: str = Form(...),
    shareLink: str = Form(None),
    price: float = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if "user" not in request.session:
        return RedirectResponse(url="/login/", status_code=303)
    article_in = ArticleCreate(
        articleTitle=articleTitle,
        articleAuthor=request.session["user"],
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price,
    )
    db_article = await create_article(db, article_in)
    return RedirectResponse(url=f"/articles/{db_article.articleID}", status_code=303)

# 글 수정
@app.get("/articles/{article_id}/edit", response_class=HTMLResponse)
async def edit_article_page(
    request: Request, article_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse(
        "edit_article.html", {"request": request, "article": article}
    )

@app.post("/articles/{article_id}/edit")
async def edit_article(
    article_id: str,
    articleTitle: str = Form(None),
    imageURL: str = Form(None),
    travelCountry: str = Form(None),
    travelCity: str = Form(None),
    shareLink: str = Form(None),
    price: float = Form(None),
    db: AsyncSession = Depends(get_db),
):
    update_in = ArticleUpdate(
        articleTitle=articleTitle,
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price,
    )
    updated = await update_article(db, article_id, update_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Article not found")
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 글 삭제
@app.post("/articles/{article_id}/delete")
async def delete_article_endpoint(article_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await delete_article(db, article_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return RedirectResponse(url="/articles/", status_code=303)

# 댓글 생성
@app.post("/articles/{article_id}/comments")
async def post_comment(
    article_id: str,
    commentAuthor: str = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    await create_comment(
        db,
        CommentCreate(articleID=article_id, commentAuthor=commentAuthor, content=content),
    )
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 댓글 수정
@app.get("/articles/{article_id}/comments/{comment_id}/edit", response_class=HTMLResponse)
async def edit_comment_page(
    request: Request, article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)
):
    art = await db.execute(select(Article).where(Article.articleID == article_id))
    if not art.scalars().first():
        raise HTTPException(status_code=404, detail="Article not found")
    com = await db.execute(select(Comment).where(Comment.commentID == comment_id))
    comment = com.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return templates.TemplateResponse(
        "edit_comment.html",
        {"request": request, "article_id": article_id, "comment": comment},
    )

@app.post("/articles/{article_id}/comments/{comment_id}/edit")
async def edit_comment(
    article_id: str,
    comment_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    updated = await update_comment(db, comment_id, CommentUpdate(content=content))
    if not updated:
        raise HTTPException(status_code=404, detail="Comment not found")
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 댓글 삭제
@app.post("/articles/{article_id}/comments/{comment_id}/delete")
async def delete_comment_endpoint(
    article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)
):
    ok = await delete_comment(db, comment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Comment not found")
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)
