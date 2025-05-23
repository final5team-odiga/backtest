from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    userID = Column(String, primary_key=True, index=True)
    userName = Column(String, nullable=False)
    userPasswordHash = Column(String, nullable=False)
    userCountry = Column(String)
    userLanguage = Column(String)
    profileImage = Column(String, nullable=True)  # 업로드한 사진 경로 저장
    
    articles = relationship("Article", back_populates="author")
    comments = relationship("Comment", back_populates="user")
    likes = relationship("Like", back_populates="user")  # Add this line

class Article(Base):
    __tablename__ = 'article'
    
    articleID = Column(String, primary_key=True, index=True)
    articleTitle = Column(String, nullable=False)
    articleAuthor = Column(String, ForeignKey('users.userID'), nullable=False)
    imageURL = Column(String)
    travelCountry = Column(String)
    travelCity = Column(String)
    createdAt = Column(DateTime, default=datetime.utcnow)
    modifiedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shareLink = Column(String)
    likes = Column(Integer, default=0)
    price = Column(Float)
    
    author = relationship("User", back_populates="articles")
    comments = relationship("Comment", back_populates="article")
    article_likes = relationship("Like", back_populates="article")  # Add this line

class Comment(Base):
    __tablename__ = 'comment'
    
    commentID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    articleID = Column(String, ForeignKey('article.articleID'), nullable=False)
    commentAuthor = Column(String, ForeignKey('users.userID'), nullable=False)
    content = Column(Text, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    modifiedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    article = relationship("Article", back_populates="comments")
    user = relationship("User", back_populates="comments")

# New model for likes
class Like(Base):
    __tablename__ = 'like'
    
    likeID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    articleID = Column(String, ForeignKey('article.articleID'), nullable=False)
    userID = Column(String, ForeignKey('users.userID'), nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
    
    article = relationship("Article", back_populates="article_likes")
    user = relationship("User", back_populates="likes")
    
    # Ensure a user can only like an article once
    __table_args__ = (
        UniqueConstraint('articleID', 'userID', name='unique_user_article_like'),
    )