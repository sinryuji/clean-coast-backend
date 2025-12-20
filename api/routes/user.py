
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import os
from dotenv import load_dotenv

from core.database import get_db
from models.user import User

load_dotenv()

router = APIRouter(
    prefix="/v1/user",
    tags=["user"]
)

security = HTTPBearer()

# JWT 설정
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str


class UserInfo(BaseModel):
    id: int
    username: str
    email: str | None = None
    created_at: datetime
    
    class Config:
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """JWT 토큰 검증"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")


@router.post("/signup", response_model=UserInfo)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    사용자 회원가입
    
    - **username**: 사용자 아이디 (고유)
    - **password**: 비밀번호
    - **email**: 이메일 (선택)
    """
    # 중복 확인
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 사용자 이름입니다")
    
    if request.email:
        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    
    # 비밀번호 해싱
    hashed_password = get_password_hash(request.password)
    
    # 사용자 생성
    new_user = User(
        username=request.username,
        password=hashed_password,
        email=request.email
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    사용자 로그인
    
    - **username**: 사용자 아이디
    - **password**: 비밀번호
    """
    # 사용자 확인
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")
    
    # 비밀번호 확인
    if not verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다")
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": user.username})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    현재 로그인한 사용자 정보 조회
    
    Authorization 헤더에 Bearer 토큰 필요
    """
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    
    return user