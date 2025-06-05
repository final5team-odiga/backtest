from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Existing schemas
class UserCreate(BaseModel):
    userID: str
    userName: str
    userPasswordHash: str
    userEmail: EmailStr
    userCountry: Optional[str] = None
    userLanguage: Optional[str] = None
    
    class Config:
        orm_mode = True

class ArticleCreate(BaseModel):
    articleTitle: str
    articleAuthor: str
    content: Optional[str]
    imageURL: Optional[str] = None
    travelCountry: str
    travelCity: str
    shareLink: Optional[str] = None
    price: Optional[float] = None
    
    class Config:
        orm_mode = True

class ArticleUpdate(BaseModel):
    articleTitle: Optional[str] = None
    content: Optional[str] = None
    imageURL: Optional[str] = None
    travelCountry: Optional[str] = None
    travelCity: Optional[str] = None
    shareLink: Optional[str] = None
    price: Optional[float] = None
    
    class Config:
        orm_mode = True

class CommentCreate(BaseModel):
    articleID: str
    commentAuthor: str
    content: str
    
    class Config:
        orm_mode = True

class CommentUpdate(BaseModel):
    content: str
    
    class Config:
        orm_mode = True

# New schema for Like
class LikeCreate(BaseModel):
    articleID: str
    userID: str
    
    class Config:
        orm_mode = True