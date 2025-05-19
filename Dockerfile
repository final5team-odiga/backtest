# # 1. 베이스 이미지 설정
# FROM python:3.10

# # 2. 작업 디렉토리 설정
# WORKDIR /app

# # 3. 앱 복사
# COPY ./app ./app
# COPY requirements.txt .

# # 4. 의존성 설치
# RUN pip install --no-cache-dir -r requirements.txt

# # 5. FastAPI 앱 실행 명령
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]

# ENV PORT=80

# 1. 베이스 이미지
FROM python:3.10

# 2. 작업 디렉터리
WORKDIR /app

# 3. 의존성 정의 복사 & 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 애플리케이션 코드 전체 복사
COPY . .

# 5. 컨테이너 포트 열기
EXPOSE 80

# 6. 환경 변수 (FastAPI 내부에서 참조할 수도 있고, docker run 시 --env-file 로 덮어쓸 수도 있습니다)
ENV PORT=80

# 7. 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
