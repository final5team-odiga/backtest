from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    userID: str
    userName: str
    userPasswordHash: str  # 비밀번호는 해시값으로 저장
    userCountry: Optional[str] = None
    userLanguage: Optional[str] = None

    class Config:
        orm_mode = True


class ArticleCreate(BaseModel):
    # articleID: str
    articleTitle: str
    articleAuthor: str
    imageURL: Optional[str] = None
    travelCountry: str
    travelCity: str
    shareLink: Optional[str] = None
    price: Optional[float] = None

    class Config:
        orm_mode = True


class ArticleUpdate(BaseModel):
    articleTitle: Optional[str] = None
    imageURL: Optional[str] = None
    travelCountry: Optional[str] = None
    travelCity: Optional[str] = None
    shareLink: Optional[str] = None
    price: Optional[float] = None

    class Config:
        orm_mode = True

# comment
class CommentCreate(BaseModel):
    articleID: str
    commentAuthor: str
    content: str

    class Config:
        from_attributes = True

class CommentUpdate(BaseModel):
    content: str

    class Config:
        from_attributes = True