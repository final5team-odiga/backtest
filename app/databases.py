# import os
# from dotenv import load_dotenv
# from pymongo import MongoClient

# # 반드시 맨 위에서 로드
# load_dotenv()

# MONGO_URI = os.getenv("MONGODB_URI")
# if not MONGO_URI:
#     raise RuntimeError(".env에서 MONGODB_URI를 찾을 수 없습니다.")

# client = MongoClient(MONGO_URI)
# db = client["fastapi-app"]
# users_collection    = db["users"]
# articles_collection = db["articles"]
# comments_collection = db["comments"]

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Azure Cosmos DB for MongoDB 연결 문자열
MONGO_URL = "mongodb+srv://user:Odiga123@odiga-mdb.global.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"

# 클라이언트 초기화
client = MongoClient(MONGO_URL)

def check_connection():
    try:
        # 연결 테스트 - 서버 정보 요청
        client.admin.command('ping')
        print("✅ MongoDB에 성공적으로 연결되었습니다.")
        return True
    except ConnectionFailure as e:
        print(f"❌ MongoDB 연결 실패: {e}")
        return False

