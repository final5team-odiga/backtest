from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, Article, Comment, Like
from app.schemas import UserCreate, ArticleCreate, ArticleUpdate, CommentCreate, CommentUpdate, LikeCreate
from sqlalchemy.orm import selectinload, Session
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
import uuid


# 비밀번호 해시화 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user(db: AsyncSession, user: UserCreate):
    hashed_password = pwd_context.hash(user.userPasswordHash)  # 비밀번호 해시화

    db_user = User(
        userID=user.userID,
        userName=user.userName,
        userPasswordHash=hashed_password,
        userEmail=user.userEmail,
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



# Add new functions for like operations
async def toggle_like(db: AsyncSession, article_id: str, user_id: str) -> dict:
    """Toggle like status for an article. Returns dict with success and liked status."""
    # Check if the user has already liked the article
    result = await db.execute(
        select(Like).where(Like.articleID == article_id, Like.userID == user_id)
    )
    existing_like = result.scalars().first()
    
    # Get article to update likes count
    article_result = await db.execute(select(Article).where(Article.articleID == article_id))
    article = article_result.scalars().first()
    if not article:
        return {"success": False, "liked": False, "likes_count": 0, "message": "Article not found"}
    
    if existing_like:
        # User already liked the article, so unlike it
        await db.delete(existing_like)
        article.likes = max(0, article.likes - 1)  # Prevent negative count
        liked = False
    else:
        # User hasn't liked the article yet, so like it
        new_like = Like(articleID=article_id, userID=user_id)
        db.add(new_like)
        article.likes += 1
        liked = True
    
    try:
        await db.commit()
        return {
            "success": True, 
            "liked": liked, 
            "likes_count": article.likes,
            "message": "Like toggled successfully"
        }
    except IntegrityError:
        await db.rollback()
        return {
            "success": False, 
            "liked": not liked, 
            "likes_count": article.likes - (1 if liked else 0),
            "message": "Error processing like"
        }

# async def toggle_like(db: AsyncSession, article_id: str, user_id: str) -> dict:
#     """Toggle like status for an article. Returns dict with success and liked status."""
#     try:
#         # Get article to update likes count
#         article_result = await db.execute(select(Article).where(Article.articleID == article_id))
#         article = article_result.scalars().first()
#         if not article:
#             return {"success": False, "liked": False, "likes_count": 0, "message": "Article not found"}
        
#         # 테이블이 없더라도 기본 기능 작동하도록 예외 처리
#         try:
#             result = await db.execute(
#                 select(Like).where(Like.articleID == article_id, Like.userID == user_id)
#             )
#             existing_like = result.scalars().first()
            
#             if existing_like:
#                 await db.delete(existing_like)
#                 article.likes = max(0, article.likes - 1)
#                 liked = False
#             else:
#                 new_like = Like(articleID=article_id, userID=user_id)
#                 db.add(new_like)
#                 article.likes += 1
#                 liked = True
#         except Exception as e:
#             # 테이블이 없는 경우 좋아요 수만 증가
#             print(f"Like table not found: {e}")
#             article.likes += 1
#             liked = True
        
#         await db.commit()
#         return {
#             "success": True, 
#             "liked": liked, 
#             "likes_count": article.likes,
#             "message": "Like toggled successfully"
#         }
#     except Exception as e:
#         await db.rollback()
#         return {
#             "success": False, 
#             "liked": False, 
#             "likes_count": 0,
#             "message": f"Error: {str(e)}"
#         }

async def check_user_liked(db: AsyncSession, article_id: str, user_id: str) -> bool:
    """Check if a user has liked an article"""
    if not user_id:
        return False
        
    result = await db.execute(
        select(Like).where(Like.articleID == article_id, Like.userID == user_id)
    )
    return result.scalars().first() is not None

# async def check_user_liked(db: AsyncSession, article_id: str, user_id: str) -> bool:
#     """Check if a user has liked an article"""
#     if not user_id:
#         return False
    
#     try:
#         result = await db.execute(
#             select(Like).where(Like.articleID == article_id, Like.userID == user_id)
#         )
#         return result.scalars().first() is not None
#     except Exception as e:
#         print(f"Error checking like status: {e}")
#         return False
