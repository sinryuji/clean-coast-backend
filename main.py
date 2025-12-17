from fastapi import FastAPI
from api.routes import trash, user

app = FastAPI(
    title="Tangyuling API",
    description="해류 및 기상 데이터 API",
    version="1.0.0"
)

# 라우터 등록
app.include_router(trash.router, prefix="/api")
app.include_router(user.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Tangyuling API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
