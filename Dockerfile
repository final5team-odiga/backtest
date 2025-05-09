# 1. 베이스 이미지 설정
FROM python:3.10

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 앱 복사
COPY ./app ./app
COPY requirements.txt .

# 4. 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. FastAPI 앱 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]

ENV PORT=80
