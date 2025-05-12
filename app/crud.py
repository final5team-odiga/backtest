from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.schemas import UserCreate
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models import Article
from app.schemas import ArticleCreate
import uuid  # uuid 모듈 임포트


# 비밀번호 해시화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(db: AsyncSession, user: UserCreate):
    hashed_password = pwd_context.hash(user.userPasswordHash)  # 비밀번호 해시화

    db_user = User(
        userID=user.userID,
        userName=user.userName,
        userPasswordHash=hashed_password,
        userCountry=user.userCountry,
        userLanguage=user.userLanguage
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


def create_article(db: Session, article: ArticleCreate):
    db_article = Article(
        articleID=str(uuid.uuid4()),
        articleTitle=article.articleTitle,
        articleAuthor=article.articleAuthor,
        imageURL=article.imageURL,
        travelCountry=article.travelCountry,
        travelCity=article.travelCity,
        shareLink=article.shareLink,
        price=article.price
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article