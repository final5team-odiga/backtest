from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Article, Comment
from app.schemas import UserCreate, ArticleCreate, ArticleUpdate, CommentCreate, CommentUpdate
from sqlalchemy.orm import selectinload, Session
from passlib.context import CryptContext
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
    #update_data = article.dict(exclude_unset=True)
    update_data = article.dict(exclude_unset=True, exclude_none=True)
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


############# 댓글 #################

# 댓글 생성
async def create_comment(db: AsyncSession, comment_in: CommentCreate) -> Comment:
    db_comment = Comment(
        articleID=comment_in.articleID,
        commentAuthor=comment_in.commentAuthor,
        content=comment_in.content
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

# 댓글 수정
async def update_comment(db: AsyncSession, comment_id: int, comment_in: CommentUpdate) -> Comment | None:
    result = await db.execute(select(Comment).where(Comment.commentID == comment_id))
    db_comment = result.scalars().first()
    if not db_comment:
        return None
    db_comment.content = comment_in.content
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

# 댓글 삭제
async def delete_comment(db: AsyncSession, comment_id: int) -> bool:
    result = await db.execute(select(Comment).where(Comment.commentID == comment_id))
    db_comment = result.scalars().first()
    if not db_comment:
        return False
    await db.delete(db_comment)
    await db.commit()
    return True