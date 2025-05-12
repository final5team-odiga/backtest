from fastapi import FastAPI, Request, Form, HTTPException, Depends  # Depends 추가
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal, get_db
from app.models import User, Article  # User 모델을 가져온다고 가정합니다.
from sqlalchemy.orm import Session
from app.schemas import ArticleCreate
from app.crud import create_article

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


# 게시글 생성 페이지
@app.get("/create_article/", response_class=HTMLResponse)
async def create_article_page(request: Request):
    return templates.TemplateResponse("create_article.html", {"request": request})

@app.post("/create_article/")
async def create_article_post(
    articleTitle: str = Form(...),
    articleAuthor: str = Form(...),
    imageURL: str = Form(...),
    travelCountry: str = Form(...),
    travelCity: str = Form(...),
    shareLink: str = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    # 게시글 생성
    article = ArticleCreate(
        articleTitle=articleTitle,
        articleAuthor=articleAuthor,
        imageURL=imageURL,
        travelCountry=travelCountry,
        travelCity=travelCity,
        shareLink=shareLink,
        price=price
    )
    db_article = create_article(db, article)
    return {"message": "Article created successfully", "article": db_article}
