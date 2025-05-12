from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    userID: str
    userName: str
    userPasswordHash: str  # 비밀번호는 해시값으로 저장
    userCountry: Optional[str] = None
    userLanguage: Optional[str] = None

    class Config:
        orm_mode = True


class ArticleCreate(BaseModel):
    articleID: str
    articleTitle: str
    articleAuthor: str
    imageURL: Optional[str] = None
    travelCountry: str
    travelCity: str
    shareLink: Optional[str] = None
    price: Optional[float] = None

    class Config:
        orm_mode = True