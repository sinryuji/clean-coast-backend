from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.routes import trash, user, chat, dashboard, report
from utils.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 lifespan 이벤트"""
    # 시작 시
    start_scheduler()
    yield
    # 종료 시
    stop_scheduler()


app = FastAPI(
    title="Tangyuling API",
    description="해류 및 기상 데이터 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(trash.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(report.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Tangyuling API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
