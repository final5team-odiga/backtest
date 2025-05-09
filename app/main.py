from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 여기서 허용할 도메인을 지정할 수 있습니다. https://victorious-forest-041ec650f.6.azurestaticapps.net
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
