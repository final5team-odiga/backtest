import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base  # Base를 반드시 import해야 합니다!
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 비동기 엔진 생성
engine = create_async_engine(DATABASE_URL, echo=True)

# 비동기 세션 설정
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency로 사용할 세션 생성
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 테이블 생성 함수
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)