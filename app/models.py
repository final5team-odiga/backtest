from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
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

    articles = relationship("Article", back_populates="author")
    comments = relationship("Comment", back_populates="user")


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

