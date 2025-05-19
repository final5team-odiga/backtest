from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.schemas import UserCreate
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models import Article
from app.schemas import ArticleCreate, ArticleUpdate
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


# def create_article(db: Session, article: ArticleCreate):
#     db_article = Article(
#         articleID=str(uuid.uuid4()),
#         articleTitle=article.articleTitle,
#         articleAuthor=article.articleAuthor,
#         imageURL=article.imageURL,
#         travelCountry=article.travelCountry,
#         travelCity=article.travelCity,
#         shareLink=article.shareLink,
#         price=article.price
#     )
#     db.add(db_article)
#     db.commit()
#     db.refresh(db_article)
#     return db_article


# (기존 create_article은 동기 세션을 썼지만, 여기서는 AsyncSession 으로 통일)
async def create_article(db: AsyncSession, article: ArticleCreate):
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
    await db.commit()
    await db.refresh(db_article)
    return db_article

async def update_article(db: AsyncSession, article_id: str, article: ArticleUpdate):
    # 1) 기존 글 로딩
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    db_article = result.scalars().first()
    if not db_article:
        return None

    # 2) 전달된 변경값만 덮어쓰기
    update_data = article.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_article, key, value)

    # 3) 커밋 & 리프레시
    await db.commit()
    await db.refresh(db_article)
    return db_article

async def delete_article(db: AsyncSession, article_id: str):
    # 1) 삭제할 글 로딩
    result = await db.execute(select(Article).where(Article.articleID == article_id))
    db_article = result.scalars().first()
    if not db_article:
        return None

    # 2) 삭제 & 커밋
    await db.delete(db_article)
    await db.commit()
    return db_article