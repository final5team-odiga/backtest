from fastapi import FastAPI, Request, Form, HTTPException, Depends  # Depends 추가
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import AsyncSessionLocal, get_db
from app.models import User, Article, Comment  # User 모델을 가져온다고 가정합니다.
from sqlalchemy.orm import Session
from app.schemas import ArticleCreate, ArticleUpdate, CommentCreate, CommentUpdate
from app.crud import create_article, update_article, delete_article, create_comment, update_comment, delete_comment

app = FastAPI()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="app/templates")

# 회원가입 모델
class UserCreate(BaseModel):
    userID: str
    userName: str
    userPasswordHash: str
    userCountry: str
    userLanguage: str

# 사용자 등록 함수 (비동기)
async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(
        userID=user.userID,
        userName=user.userName,
        userPasswordHash=user.userPasswordHash,
        userCountry=user.userCountry,
        userLanguage=user.userLanguage
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# 회원가입 폼 렌더링
@app.get("/signup/", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# 회원가입 처리
@app.post("/signup/")
async def signup(userID: str = Form(...), userName: str = Form(...), userPasswordHash: str = Form(...), userCountry: str = Form(...), userLanguage: str = Form(...), db: AsyncSession = Depends(get_db)):  # Depends 추가
    # 이미 존재하는 사용자 확인
    result = await db.execute(select(User).filter(User.userID == userID))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists.")

    # 사용자 생성
    user = UserCreate(
        userID=userID,
        userName=userName,
        userPasswordHash=userPasswordHash,
        userCountry=userCountry,
        userLanguage=userLanguage
    )
    new_user = await create_user(db, user)  # 비동기로 사용자 데이터베이스에 추가
    return {"message": "회원 가입이 완료되었습니다.", "user": new_user}


# # 게시글 생성 페이지
# @app.get("/create_article/", response_class=HTMLResponse)
# async def create_article_page(request: Request):
#     return templates.TemplateResponse("create_article.html", {"request": request})

# @app.post("/create_article/")
# async def create_article_post(
#     articleTitle: str = Form(...),
#     articleAuthor: str = Form(...),
#     imageURL: str = Form(...),
#     travelCountry: str = Form(...),
#     travelCity: str = Form(...),
#     shareLink: str = Form(...),
#     price: float = Form(...),
#     db: Session = Depends(get_db)
# ):
#     # 게시글 생성
#     article = ArticleCreate(
#         articleTitle=articleTitle,
#         articleAuthor=articleAuthor,
#         imageURL=imageURL,
#         travelCountry=travelCountry,
#         travelCity=travelCity,
#         shareLink=shareLink,
#         price=price
#     )
#     db_article = create_article(db, article)
#     return {"message": "Article created successfully", "article": db_article}

# ── 1) 글 목록 ─────────────────────────────────────────
@app.get("/articles/", response_class=HTMLResponse)
async def list_articles(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).order_by(Article.createdAt.desc()))
    articles = result.scalars().all()
    return templates.TemplateResponse("articles.html", {
        "request": request,
        "articles": articles
    })


# ── 2) 글 상세 ─────────────────────────────────────────
@app.get("/articles/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # 댓글 목록 조회
    comments_result = await db.execute(select(Comment).where(Comment.articleID == article_id).order_by(Comment.createdAt.asc()))
    comments = comments_result.scalars().all()

    
    return templates.TemplateResponse("article_detail.html", {
        "request": request,
        "article": article,
        "comments": comments
    })


# ── 3) 글 생성 ─────────────────────────────────────────
@app.get("/create_article/", response_class=HTMLResponse)
async def create_article_page(request: Request):
    return templates.TemplateResponse("create_article.html", {"request": request})

@app.post("/create_article/")
async def create_article_post(
    articleTitle: str = Form(...),
    articleAuthor: str = Form(...),
    imageURL: str = Form(None),
    travelCountry: str = Form(...),
    travelCity: str = Form(...),
    shareLink: str = Form(None),
    price: float = Form(None),
    db: AsyncSession = Depends(get_db)
):
    article_in = ArticleCreate(
        articleTitle=articleTitle,
        articleAuthor=articleAuthor,
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price
    )
    db_article = await create_article(db, article_in)
    return RedirectResponse(url=f"/articles/{db_article.articleID}", status_code=303)


# ── 4) 글 수정 ─────────────────────────────────────────
@app.get("/articles/{article_id}/edit", response_class=HTMLResponse)
async def edit_article_page(request: Request, article_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return templates.TemplateResponse("edit_article.html", {
        "request": request,
        "article": article
    })

@app.post("/articles/{article_id}/edit")
async def edit_article(
    article_id: str,
    articleTitle: str = Form(None),
    imageURL: str = Form(None),
    travelCountry: str = Form(None),
    travelCity: str = Form(None),
    shareLink: str = Form(None),
    price: float = Form(None),
    db: AsyncSession = Depends(get_db)
):
    update_in = ArticleUpdate(
        articleTitle=articleTitle,
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price
    )
    updated = await update_article(db, article_id, update_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Article not found")
    return RedirectResponse(url=f"/articles/{article_id}", status_code=303)


# ── 5) 글 삭제 ─────────────────────────────────────────
@app.post("/articles/{article_id}/delete")
async def delete_article_endpoint(
    article_id: str,
    db: AsyncSession = Depends(get_db)
):
    deleted = await delete_article(db, article_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return RedirectResponse(url="/articles/", status_code=303)


# 댓글 생성 (기존)
@app.post("/articles/{article_id}/comments")
async def post_comment(
    article_id: str,
    commentAuthor: str = Form(...),
    content: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # (작성자 검증 생략)
    await create_comment(db, CommentCreate(
        articleID=article_id,
        commentAuthor=commentAuthor,
        content=content
    ))
    return RedirectResponse(f"/articles/{article_id}", status_code=303)

# 댓글 수정 폼
@app.get("/articles/{article_id}/comments/{comment_id}/edit", response_class=HTMLResponse)
async def edit_comment_page(request: Request, article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)):
    # 글 존재 확인
    art = await db.execute(select(Article).where(Article.articleID == article_id))
    if not art.scalars().first():
        raise HTTPException(404, "Article not found")
    # 댓글 로드
    com = await db.execute(select(Comment).where(Comment.commentID == comment_id))
    comment = com.scalars().first()
    if not comment:
        raise HTTPException(404, "Comment not found")
    return templates.TemplateResponse("edit_comment.html", {
        "request": request,
        "article_id": article_id,
        "comment": comment
    })

# 댓글 수정 처리
@app.post("/articles/{article_id}/comments/{comment_id}/edit")
async def edit_comment(
    article_id: str,
    comment_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    updated = await update_comment(db, comment_id, CommentUpdate(content=content))
    if not updated:
        raise HTTPException(404, "Comment not found")
    return RedirectResponse(f"/articles/{article_id}", status_code=303)

# 댓글 삭제 처리
@app.post("/articles/{article_id}/comments/{comment_id}/delete")
async def delete_comment_endpoint(article_id: str, comment_id: int, db: AsyncSession = Depends(get_db)):
    ok = await delete_comment(db, comment_id)
    if not ok:
        raise HTTPException(404, "Comment not found")
    return RedirectResponse(f"/articles/{article_id}", status_code=303)