from fastapi import FastAPI, Request, Form, HTTPException, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
import os
from zoneinfo import ZoneInfo

from app.database import get_db
from app.models import User, Article, Comment, Like
from app.schemas import UserCreate, ArticleCreate, ArticleUpdate, CommentCreate, CommentUpdate, LikeCreate
from app.crud import (
    create_article,
    update_article,
    delete_article,
    create_comment,
    update_comment,
    delete_comment,
    toggle_like,
    check_user_liked,
)
from passlib.context import CryptContext

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="app/templates")


# 일단 시작페이지 articles로 리다이렉트
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # articles 목록으로 리디렉션
    return RedirectResponse(url="/articles/", status_code=303)




# 세션 미들웨어 설정
load_dotenv()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))

# 현재 로그인된 사용자 체크
async def get_current_user(request: Request):
    user_id = request.session.get("user")
    if not user_id:
        return None
    return user_id

# 회원가입 핸들러: 비밀번호 해싱하여 DB에 저장
@app.get("/signup/", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup/")
async def signup(
    request: Request,
    userID: str = Form(...),
    userName: str = Form(...),
    password: str = Form(...),
    userCountry: str = Form(...),
    userLanguage: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # 중복 확인
    result = await db.execute(select(User).where(User.userID == userID))
    if result.scalar_one_or_none():
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": "이미 존재하는 사용자입니다."},
            status_code=400,
        )
    # 비밀번호 해싱
    hashed_pw = pwd_context.hash(password)
    user_in = UserCreate(
        userID=userID,
        userName=userName,
        userPasswordHash=hashed_pw,
        userCountry=userCountry,
        userLanguage=userLanguage,
    )
    # 직접 User 모델 생성
    db_user = User(
        userID=user_in.userID,
        userName=user_in.userName,
        userPasswordHash=user_in.userPasswordHash,
        userCountry=user_in.userCountry,
        userLanguage=user_in.userLanguage,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return RedirectResponse(url="/login/", status_code=303)

# 로그인
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
    return RedirectResponse(url="/articles/", status_code=303)

# 글 목록
@app.get("/articles/", response_class=HTMLResponse)
async def list_articles(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).order_by(Article.createdAt.desc()))
    articles = result.scalars().all()
    return templates.TemplateResponse("articles.html", {"request": request, "articles": articles})

# 글 상세 및 댓글 목록
@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    ### 클라이언트 시간 js로 받아와서 timezone으로)
    #tz = ZoneInfo(timezone)
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    comments_result = await db.execute(
        select(Comment).where(Comment.articleID == article_id).order_by(Comment.createdAt.asc())
    )
    comments = comments_result.scalars().all()
    return templates.TemplateResponse(
        "article_detail.html",
        {"request": request, "article": article, "comments": comments},
    )

# 글 생성 (로그인 필요)
@app.get("/create_article/", response_class=HTMLResponse)
async def create_article_page(request: Request):
    user_id = request.session.get("user")
    if not request.session.get("user"):
        return RedirectResponse(url="/login/", status_code=303)
    return templates.TemplateResponse("create_article.html", {"request": request, "user_id": user_id})

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
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    article_in = ArticleCreate(
        articleTitle=articleTitle,
        articleAuthor=user_id,
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price,
    )
    db_article = await create_article(db, article_in)
    return RedirectResponse(url=f"/articles/{db_article.articleID}", status_code=303)


# 글 수정 (로그인 및 작성자 확인)
@app.get("/articles/{article_id}/edit", response_class=HTMLResponse)
async def edit_article_page(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.articleAuthor != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")
    return templates.TemplateResponse("edit_article.html", {"request": request, "article": article})

@app.post("/articles/{article_id}/edit")
async def edit_article(request: Request, article_id: str,
                        articleTitle: str = Form(None), imageURL: str = Form(None),
                        travelCountry: str = Form(None), travelCity: str = Form(None),
                        shareLink: str = Form(None), price: float = Form(None),
                        db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.articleAuthor != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")
    update_in = ArticleUpdate(articleTitle=articleTitle, imageURL=imageURL,
                               travelCountry=travelCountry, travelCity=travelCity,
                               shareLink=shareLink, price=price)
    await update_article(db, article_id, update_in)
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 글 삭제 (로그인 및 작성자 확인)
@app.post("/articles/{article_id}/delete")
async def delete_article_endpoint(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if article.articleAuthor != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this article")
    await delete_article(db, article_id)
    return RedirectResponse(url="/articles/", status_code=303)

# 댓글 생성
@app.post("/articles/{article_id}/comments")
async def post_comment(request: Request, article_id: str,
                        content: str = Form(...), db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    await create_comment(db, CommentCreate(articleID=article_id,
                                          commentAuthor=user_id,
                                          content=content))
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 댓글 수정
@app.get("/articles/{article_id}/comments/{comment_id}/edit", response_class=HTMLResponse)
async def edit_comment_page(request: Request, article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    art = await db.execute(select(Article).where(Article.articleID == article_id))
    if not art.scalars().first():
        raise HTTPException(status_code=404, detail="Article not found")
    com = await db.execute(select(Comment).where(Comment.commentID == comment_id))
    comment = com.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.commentAuthor != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")
    return templates.TemplateResponse("edit_comment.html", {"request": request, "article_id": article_id, "comment": comment})

@app.post("/articles/{article_id}/comments/{comment_id}/edit")
async def edit_comment(request: Request, article_id: str, comment_id: int,
                        content: str = Form(...), db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    await update_comment(db, comment_id, CommentUpdate(content=content))
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)

# 댓글 삭제
@app.post("/articles/{article_id}/comments/{comment_id}/delete")
async def delete_comment_endpoint(request: Request, article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    if not user_id:
        return RedirectResponse(url="/login/", status_code=303)
    await delete_comment(db, comment_id)
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)


@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    user_id = request.session.get("user")
    
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    comments_result = await db.execute(
        select(Comment).where(Comment.articleID == article_id).order_by(Comment.createdAt.asc())
    )
    comments = comments_result.scalars().all()
    
    # Check if the logged-in user has liked this article
    user_liked = await check_user_liked(db, article_id, user_id) if user_id else False
    
    return templates.TemplateResponse(
        "article_detail.html",
        {
            "request": request, 
            "article": article, 
            "comments": comments,
            "user_id": user_id,
            "user_liked": user_liked
        },
    )

# Toggle like endpoint (AJAX)
@app.post("/articles/{article_id}/like")
async def like_article(
    request: Request, 
    article_id: str, 
    db: AsyncSession = Depends(get_db)
):
    user_id = request.session.get("user")
    if not user_id:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Login required to like articles"}
        )
    
    result = await toggle_like(db, article_id, user_id)
    return JSONResponse(content=result)